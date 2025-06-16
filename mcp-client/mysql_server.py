import csv
import json
from mcp.server.fastmcp import FastMCP
import pymysql

mcp = FastMCP("MySQLServer")
USER_AGENT = "MySQLserver-app/1.0"


def get_connection():
    return pymysql.connect(
        host="localhost",  # 数据库地址
        user="root",  # 数据库用户名
        passwd="Xiaxl.901208",  # 数据库密码
        db="school",  # 数据库名
        charset="utf8",  # 字符集选择utf8
    )


@mcp.tool()
async def sql_inter(sql):
    """
    查询本地MySQL数据库，通过运行一段SQL代码来进行数据库查询。\
    :param sql: 字符串形式的SQL查询语句，用于执行对MySQL中school数据库中各张表进行查询，并获得各表中的各类相关信息
    :return：sql在MySQL中的运行结果。
    """

    connection = get_connection()
    results = ()

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()
    finally:
        connection.close()

    return json.dumps(results)


@mcp.tool()
async def export_table_to_csv(table_name, output_file):
    """
    将 MySQL 数据库中的某个表导出为 CSV 文件。

    :param table_name: 需要导出的表名
    :param output_file: 输出的 CSV 文件路径
    """

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # 查询数据表的所有数据
            query = f"SELECT * FROM {table_name};"
            cursor.execute(query)
            # 获取所有列名
            column_names = [desc[0] for desc in cursor.description]

            # 获取查询结果
            rows = cursor.fetchall()

            # 将数据写入 CSV 文件
            with open(output_file, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)

                # 写入表头
                writer.writerow(column_names)

                # 写入数据
                writer.writerows(rows)

            print(f"数据表 {table_name} 已成功导出至 {output_file}")

    finally:
        connection.close()


if __name__ == "__main__":
    # 以标准 I/O 方式运行 MCP 服务器
    mcp.run(transport="stdio")
