## Hi there 👋

<!--
**dandyhair/dandyhair** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.

Here are some ideas to get you started:

- 🔭 I’m currently working on ...
- 🌱 I’m currently learning ...
- 👯 I’m looking to collaborate on ...
- 🤔 I’m looking for help with ...
- 💬 Ask me about ...
- 📫 How to reach me: ...
- 😄 Pronouns: ...
- ⚡ Fun fact: ...
-->
打开浏览器访问 http://127.0.0.1:5000，首次登录时输入任意用户名和密码即可自动注册并进入系统。

2️⃣ 云端部署（推荐用于日常实际使用）
这里以 Render.com 免费服务为例，部署后即可获得一个 https://xxx.onrender.com 的永久访问地址，电脑与手机均可使用。

准备工作
将本项目推送到你自己的 GitHub 仓库（已推送可跳过）

注册 Render 账号（可直接用 GitHub 登录）

部署步骤
登录 Render 后，点击右上角 New + → Web Service

授权连接你的 GitHub，选择本仓库

Render 会自动识别项目类型为 Python，无需修改

填写以下关键信息：

Build Command：pip install -r requirements.txt

Start Command：gunicorn app:app

Instance Type：选择 Free

点击 Create Web Service，等待部署完成（约 2-3 分钟）

部署成功后，页面顶部显示的 https://你的服务名.onrender.com 即为你的云端地址

移动端访问
电脑端：直接访问 https://你的服务名.onrender.com

手机端：访问 https://你的服务名.onrender.com/mobile，获得适配触摸操作的移动版界面

提示：免费 Render 实例在 15 分钟无访问后会自动休眠，再次访问时会有短暂唤醒时间（约 30 秒），不影响使用。

3️⃣ 其他部署平台（备选）
也支持部署到 PythonAnywhere、Railway 等平台，只需配置好启动命令（通常是 gunicorn app:app）和环境变量即可。

📁 项目结构
text
haircare-finance/
├── app.py                    # Flask 主程序（API + 数据库模型 + 登录）
├── requirements.txt          # Python 依赖清单
├── README.md                 # 本说明文件
├── static/
│   ├── css/
│   │   └── style.css         # 桌面版样式
│   └── js/
│       ├── app.js            # 桌面版前端逻辑
│       └── app-mobile.js     # 移动版前端逻辑
├── templates/
│   ├── login.html            # 登录/注册页面
│   ├── index.html            # 桌面版主界面
│   └── mobile.html           # 手机版主界面
└── data/
    └── initial_data.json     # 示例数据（可用于导入系统预览）
🔐 关于数据安全
所有数据默认存储在服务器端的 finance.db SQLite 数据库中

每个用户的数据完全隔离，多用户互不可见

密码使用哈希加密存储，不会明文保存

建议定期使用系统内的“导出全部数据”功能进行手动备份

免费 Render 部署的数据库文件可能因实例重启而重置，强烈建议养成定期导出的习惯

🧠 技术栈
后端：Python / Flask / Flask-SQLAlchemy / Flask-Login

前端：原生 HTML + CSS + JavaScript，图表使用 Chart.js

数据库：SQLite（可轻松切换为 PostgreSQL 等）

部署：gunicorn（生产环境），Render 提供免费 HTTPS 托管

📝 待扩展功能（欢迎贡献）
支出分类/收入平台的图表联动筛选

更细颗粒度的权限控制（只读用户等）

数据可视化大屏模式

导出 Excel 报表功能

📧 联系方式
如果你在使用过程中遇到问题，欢迎在 GitHub 提交 Issue。

如果你觉得这个项目有用，请给一个 ⭐ Star 支持一下！

text

