"""完整导入 .xls → 财务系统（收入+支出+店铺+供应商）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Income, Expense
import xlrd, json
from datetime import datetime, timedelta

XLS_PATH = r'C:\Users\dannl\Downloads\常用20260512修改供应商和1-5月进出入账目数据.xls'
TARGET_USER = 'dandyhair'

def excel_serial_to_date(serial):
    if isinstance(serial, float) and serial > 40000:
        return (datetime(1899, 12, 30) + timedelta(days=int(serial))).strftime('%Y-%m-%d')
    return None

# ========== 主流程 ==========
wb = xlrd.open_workbook(XLS_PATH)
all_names = wb.sheet_names()

# 按位置区分工作表（.xls编码问题，不能用中文匹配）
# 前5个=营业额(收入), 接着5个=费用支出, 然后店铺管理, 最后供应商管理
income_names = all_names[0:5]
expense_names = []
shop_name = None
supplier_name = None
for n in all_names[5:]:
    if '费用' in n:
        expense_names.append(n)
    elif '供应商' in n:
        supplier_name = n
    else:
        shop_name = n

print('收入表:', income_names)
print('支出表:', expense_names)
print('店铺表:', shop_name)
print('供应商表:', supplier_name)

with app.app_context():
    user = User.query.filter_by(username=TARGET_USER).first()
    if not user:
        print(f'ERROR: 用户 {TARGET_USER} 不存在')
        sys.exit(1)
    print(f'\n用户: {TARGET_USER} (id={user.id})')

    # ========== 1. 读取店铺管理 → 构建 shop_name → platform 映射 ==========
    shop_map = {}
    platform_shops = {}

    if shop_name:
        ws = wb.sheet_by_name(shop_name)
        print(f'\n读取店铺管理: {ws.nrows}行')
        for r in range(1, ws.nrows):
            shop_name_val = str(ws.cell_value(r, 2)).strip()
            platform = str(ws.cell_value(r, 1)).strip()
            if shop_name_val and platform:
                shop_map[shop_name_val] = platform
                if platform not in platform_shops:
                    platform_shops[platform] = []
                if shop_name_val not in platform_shops[platform]:
                    platform_shops[platform].append(shop_name_val)
        print(f'  共 {len(shop_map)} 个店铺 → {len(platform_shops)} 个平台')

    # ========== 2. 读取供应商 ==========
    suppliers = []
    if supplier_name:
        ws = wb.sheet_by_name(supplier_name)
        for r in range(2, ws.nrows):
            v = str(ws.cell_value(r, 0)).strip()
            if v and len(v) > 1:
                suppliers.append(v)
        print(f'\n读取供应商: {len(suppliers)} 个')

    # ========== 3. 清除 2026年1-5月数据 ==========
    del_inc = 0
    del_exp = 0
    for inc in Income.query.filter_by(user_id=user.id).all():
        d = inc.date
        if d and d.startswith('2026-0'):
            db.session.delete(inc)
            del_inc += 1
    for exp in Expense.query.filter_by(user_id=user.id).all():
        d = exp.date
        if d and d.startswith('2026-0'):
            db.session.delete(exp)
            del_exp += 1
    db.session.commit()
    print(f'\n清除旧数据: 收入 {del_inc} 条, 支出 {del_exp} 条')

    # ========== 4. 导入收入 ==========
    total_inc = 0
    inc_platforms = set()
    inc_shops_map = {}

    for sname in income_names:
        try:
            ws = wb.sheet_by_name(sname)
        except:
            continue

        # 读取表头 (行1)
        headers = {}
        for c in range(2, ws.ncols - 2):  # 跳过最后2列(备注+汇总)
            h = str(ws.cell_value(1, c)).strip()
            if h:
                headers[c] = h

        batch = []
        for r in range(2, ws.nrows):
            date_str = excel_serial_to_date(ws.cell_value(r, 1))
            if not date_str:
                continue

            for c, shop_name in headers.items():
                amount = ws.cell_value(r, c)
                if not amount or amount == '':
                    continue
                try:
                    amt = float(amount)
                except (ValueError, TypeError):
                    continue
                if amt <= 0:
                    continue

                # 查找平台
                platform = shop_map.get(shop_name, None)
                if platform is None:
                    # 5月份列名简化了，模糊匹配
                    for sn, p in shop_map.items():
                        if shop_name in sn or sn in shop_name:
                            platform = p
                            shop_name = sn
                            break
                if platform is None:
                    platform = '其他'

                inc_platforms.add(platform)
                if platform not in inc_shops_map:
                    inc_shops_map[platform] = set()
                inc_shops_map[platform].add(shop_name)

                batch.append(Income(
                    user_id=user.id, date=date_str, platform=platform,
                    shop=shop_name, amount=amt,
                    withdraw_date='', withdraw_amount=0, note=''
                ))
                if len(batch) >= 300:
                    db.session.add_all(batch)
                    db.session.commit()
                    total_inc += len(batch)
                    batch = []
        if batch:
            db.session.add_all(batch)
            db.session.commit()
            total_inc += len(batch)
        print(f'  {sname}: 已导入')

    print(f'\n收入导入完成: {total_inc} 条')

    # ========== 5. 导入费用支出 ==========
    total_exp = 0

    for sname in expense_names:
        try:
            ws = wb.sheet_by_name(sname)
        except:
            continue

        # 找金额列：扫描第2行看哪列有数值
        amount_col = None
        for c in range(ws.ncols - 1, 2, -1):
            v = ws.cell_value(3, c)  # 第3行数据
            if v and v != '':
                try:
                    float(v)
                    amount_col = c
                    break
                except:
                    continue
        if amount_col is None:
            amount_col = 13  # 默认N列

        batch = []
        for r in range(2, ws.nrows):
            date_str = excel_serial_to_date(ws.cell_value(r, 1))
            if not date_str:
                continue
            summary = str(ws.cell_value(r, 2) or '').strip()
            if not summary:
                # 可能是空行
                continue

            amount = ws.cell_value(r, amount_col)
            try:
                amt = float(amount)
            except (ValueError, TypeError):
                continue
            if amt <= 0:
                continue

            batch.append(Expense(
                user_id=user.id, date=date_str, payment='', supplier='',
                amount=amt, category='采购', note=summary
            ))
            if len(batch) >= 200:
                db.session.add_all(batch)
                db.session.commit()
                total_exp += len(batch)
                batch = []
        if batch:
            db.session.add_all(batch)
            db.session.commit()
            total_exp += len(batch)
        print(f'  {sname}: 已导入 {total_exp} 条累计')

    print(f'\n支出导入完成: {total_exp} 条')

    # ========== 6. 更新用户设置 ==========
    platform_order = ['拼多多', '抖音', '淘宝', '快手', '微信', 'TikTok', '阿里巴巴']
    ordered = [p for p in platform_order if p in inc_platforms]
    for p in sorted(inc_platforms):
        if p not in ordered:
            ordered.append(p)

    shops_dict = {}
    for p in ordered:
        shops_dict[p] = sorted(inc_shops_map.get(p, []))

    user.platforms = json.dumps(ordered, ensure_ascii=False)
    user.shops = json.dumps(shops_dict, ensure_ascii=False)
    if suppliers:
        user.suppliers = json.dumps(suppliers, ensure_ascii=False)

    existing_cats = set(user.get_expense_categories())
    existing_cats.add('采购')
    user.expense_categories = json.dumps(sorted(existing_cats), ensure_ascii=False)

    db.session.commit()

    print(f'\n===== 导入完成 =====')
    print(f'收入: {total_inc} 条')
    print(f'支出: {total_exp} 条')
    print(f'平台: {ordered}')
    for p in ordered:
        print(f'  {p} ({len(shops_dict[p])}店): {shops_dict[p][:5]}...' if len(shops_dict[p]) > 5 else f'  {p}: {shops_dict[p]}')
    print(f'供应商: {len(suppliers)} 个')
    print(f'\n重启 Flask 刷新即可。')
