import threading
from common.log import logger
from config import conf
from plugins.plugin_comm.api.api_groupx import ApiGroupx
from plugins.plugin_comm.plugin_comm import EthZero


class SyncContractsRooms(object):
    def __init__(self, rooms, contracts):
        super().__init__()
        self.rooms = []
        # 使用列表推导式转换字典为列表
        for key, value in rooms.items():
            m_list = []
            member_list = value.get("member_list", [])
            for kkk in member_list:
                vvv = member_list.get(kkk)
                m = {
                    "wxid": kkk,
                    "alias": vvv.get("alias"),
                    "code": vvv.get("code"),
                    "Country": vvv.get("country"),
                    "City": vvv.get("city"),
                    "Sex": 1 if vvv.get("gender") == "男" else 0,
                    "Province": vvv.get("province"),
                    "NickName": vvv.get("name")
                    or vvv.get("nickname")
                    or vvv.get("display_name"),
                    "UserName": kkk,
                }
                m_list.append(m)

            item = {
                "MemberList": m_list,
                "NickName": value.get("nickname"),
                "UserName": key,
                "wxid": key,
            }
            self.rooms.append(item)
            # rooms[key] = {"member_list": value.get("member_list")}

        self.contacts = [
            {
                "wxid": key,
                "alias": value.get("alias"),
                "code": value.get("code"),
                "Country": value.get("country"),
                "City": value.get("city"),
                "Sex": 1 if value.get("gender") == "男" else 0,
                "Province": value.get("province"),
                "NickName": value.get("name"),
                "UserName": key,
            }
            for key, value in contracts.items()
        ]

        self.postFriendsPos = 0
        self.postGroupsPos = 0

        self.groupx = ApiGroupx()
        self.robot_account = conf().get("bot_account", EthZero)
        self.robot_name = conf().get("bot_name")

    def postWxInfo2Groupx(self):
        self.postContracts2Groupx()
        self.postGroups2Groupx()

    def postContracts2Groupx(self):
        step = 300
        if not self.contacts or len(self.contacts) == 0:
            logger.error("[WX] postContracts2Groupx:contracts is empty")
            return

        end = self.postFriendsPos + step
        if end > len(self.contacts):
            end = len(self.contacts) - 1

        friends = self.contacts[self.postFriendsPos : end]
        logger.info(
            f"post friends to server :{self.postFriendsPos}->{end},本次:{len(friends)}个,总共:{len(self.contacts)}"
        )

        self.postFriendsPos += step
        if len(friends) < step:
            # 全部好友都发送完成了
            self.postFriendsPos = 0
            logger.info(f"好友列表发送完成,共{len(self.contacts)}个好友")
        else:
            # 每隔8秒执行一次,直到好友列表全部发送完成
            threading.Timer(8.0, self.postContracts2Groupx).start()

        ret = self.groupx.post_friends(
            self.robot_account, self.robot_name, friends, "wcferry"
        )
        if ret is False:
            logger.error(f"post friends to groupx failed ${ret}")
            return False
        else:
            logger.info(f"post friends to groupx success 用户数:{len(ret)}")

        return ret

    def postGroups2Groupx(self):
        if not self.rooms or len(self.rooms) == 0:
            logger.error("[WX] postGroups2Groupx:rooms is empty")
            return

        step = 20

        chatrooms = self.rooms[self.postGroupsPos : self.postGroupsPos + step]
        self.postGroupsPos += step
        if len(chatrooms) < step:
            self.postGroupsPos = 0
            logger.info(f"群列表已发送完成,共:{len(self.rooms)}")
        else:
            # 每隔20秒执行一次,直到群列表全部发送完成
            threading.Timer(17.0, self.postGroups2Groupx).start()

        ret = self.groupx.post_groups(
            self.robot_account, self.robot_name, chatrooms, "wcferry"
        )
        logger.info(
            f"post groups to server:位置:{self.postGroupsPos}, 共:{len(self.rooms)}, 返回数组长度:{len(ret)}"
        )
        # self._set_remark_name_chatrooms(ret)
        return ret
