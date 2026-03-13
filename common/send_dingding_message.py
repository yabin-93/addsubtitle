import requests


class SendReportMessage:
    @staticmethod
    def send_dingtalk_message(data):
        url = "https://oapi.dingtalk.com/robot/send?access_token=c3b776fd3180725e91e79b878a97d70347527444e9e8e08483fc10cb9022f776"
        # 测试2
        # url = "https://oapi.dingtalk.com/robot/send?access_token=9bf28517257699028b1583025a3cc14e46c030254529e1497ff8101c653b0208"
        params = {"text": {"content": data}, "msgtype": "text"}
        res = requests.post(url=url, json=params).json()
        print(res)


if __name__ == '__main__':
    send = SendReportMessage()
    send.send_dingtalk_message("api_auto自动化测试报告")
