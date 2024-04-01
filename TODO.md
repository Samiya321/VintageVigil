
### TODO List
- [ ] 配置文件中增加用户到期时间项，以自动停止过期用户任务
- [ ] 数据库中增加用户名项，以区分多用户数据
- [x] 程序运行时允许自定义传入用户配置文件路径 -r -u
- [ ] 测试hoyoyo的surugaya
- [x] 优化docker容器打包后镜像大小及内存占用问题，清理不必要的文件，避免缓存文件被添加到镜像中。
- [x] 以Alpine为底包打包一份docker镜像，镜像体积更小，运行时的资源占用也较低
- [ ] 配置文件热重载问题
- [ ] 将监控系统接入telegram bot，以允许随时添加用户配置文件 或者停止用户任务
- [ ] Alpine的一键DD脚本
- [ ] 对于煤炉推送时间不一样的现象 观察它属于哪个排序？
- [ ] 煤炉缓存问题 1. 请求链接加时间戳 2. 请求头中的Origin和Accept-Encoding是否有影响
- [ ] https://api.mercari.jp/users/get_profile?user_id=193978404&_user_format=profile 该接口返回email和phone_number，不知是否需要登录才返回？
- [ ] 煤炉过滤器的值，映射
- [ ] paypay和fril的过滤还没对
- [x] 请求链接是否一定要https？
- [ ] 内存优化