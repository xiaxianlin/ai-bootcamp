class Console:
    @staticmethod
    def log(content):
        print(">>>" + "=" * 10 + "[开始]" + "=" * 10 + "<<<")
        print(content)
        print(">>>" + "=" * 10 + "[结束]" + "=" * 10 + "<<<\n")
