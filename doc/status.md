状态属性

# 正常平台
0 售出
1 在售

00
01 商品补货 推送

10
11 价格变动 判断涨价降价 由配置文件决定是否推送


# suruga平台 价格取本店价格和第三方价格中的最小值，如均不存在(即均无货时)，价格为0
0 本店及第三方店铺均售空 
1 本店及第三方店铺均在售
2 本店在售 第三方店铺售空
3 本店售空 第三方店铺在售

00 
01 本店及第三方店铺均补货
02 本店补货
03 第三方店铺补货

10 
11 价格变动 判断涨价降价 由配置文件决定是否推送
12 第三方店铺售出，价格可能变动或者不变动
13 本店售出，价格可能变动或者不变动

20 
21 第三方补货，价格可能变动
22 价格变动 判断涨价降价 由配置文件决定是否推送
23 本店售出，第三方补货，价格可能变动

30 
31 本店补货
32 本店补货，第三方售出
33 价格变动 判断涨价降价 由配置文件决定是否推送


00 10 20 30 售出 0结尾
11 12 13 22 33 价格变动 两个数字相同 或者以1开头
01 02 03 21 23 31 32 补货 
