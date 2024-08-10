import threading
from common.log import logger
from config import conf
from plugins.plugin_comm.api.api_groupx import ApiGroupx
from plugins.plugin_comm.plugin_comm import EthZero

class SyncContractsRooms(object):
    def __init__(self,rooms,contracts):
        super().__init__()
        self.rooms_ary = rooms
        self.contracts_ary = contracts
        
        self.postFriendsPos = 0
        self.postGroupsPos = 0
        
        self.groupx = ApiGroupx()
        self.robot_account = conf().get("bot_account", EthZero)
        self.robot_name = conf().get("bot_name")

    def postWxInfo2Groupx(self):
        self.postContracts2Groupx()
        self.postGroups2Groupx()

    def postContracts2Groupx(self):
        step = 50
        if not self.contracts_ary or len(self.contracts_ary) == 0:
            logger.error("[WX] postContracts2Groupx:contracts is empty")
            return

        end = self.postFriendsPos + step
        if end > len(self.contracts_ary):
            end = len(self.contracts_ary) - 1

        friends = self.contracts_ary[self.postFriendsPos : end]
        logger.info(
            f"post friends to server :{self.postFriendsPos}->{end},本次:{len(friends)}个,总共:{len(self.contracts_ary)}"
        )

        self.postFriendsPos += step
        if len(friends) < step:
            # 全部好友都发送完成了
            self.postFriendsPos = 0
            logger.info(f"好友列表发送完成,共{len(self.contracts_ary)}个好友")
        else:
            # 每隔8秒执行一次,直到好友列表全部发送完成
            threading.Timer(8.0, self.postContracts2Groupx).start()

        ret = self.groupx.post_friends(self.robot_account, self.robot_name, friends,"wcferry")
        if ret is False:
            logger.error(f"post friends to groupx failed ${ret}")
            return False
        else:
            logger.info(f"post friends to groupx success 用户数:{len(ret)}")

        return ret

    def postGroups2Groupx(self):
        if not self.rooms_ary or len(self.rooms_ary) == 0:
            logger.error("[WX] postGroups2Groupx:rooms is empty")
            return

        step = 50

        chatrooms = self.rooms_ary[self.postGroupsPos : self.postGroupsPos + step]
        self.postGroupsPos += step
        if len(chatrooms) < step:
            self.postGroupsPos = 0
            logger.info(f"群列表已发送完成,共:{len(self.rooms_ary)}")
        else:
            # 每隔20秒执行一次,直到群列表全部发送完成
            threading.Timer(17.0, self.postGroups2Groupx).start()

        ret = self.groupx.post_groups(self.robot_account, self.robot_name, chatrooms,"wcferry")
        logger.info(
            f"post groups to server:位置:{self.postGroupsPos}, 共:{len(self.rooms_ary)}, 返回数组长度:{len(ret)}"
        )
        # self._set_remark_name_chatrooms(ret)
        return ret



