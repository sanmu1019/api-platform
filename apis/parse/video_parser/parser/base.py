import dataclasses
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List
import fake_useragent


class VideoSource(Enum):
    """
    视频来源：douiyin，kuaishou...
    """
    DouYin = "douyin"
    KuaiShou = "kuaishou"
    PiPiXia = "pipixia"
    WeiBo = "weibo"
    RedBook = "redbook"
    XiGua = "xigua"
    AcFun = "acfun"


@dataclasses.dataclass
class VideoAuthor:
    uid: str = ""
    name: str = ""
    avatar: str = ""


@dataclasses.dataclass
class ImgInfo:
    url: str = ""
    live_photo_url: str = ""


@dataclasses.dataclass
class VideoInfo:
    video_url: str
    cover_url: str
    title: str = ""
    music_url: str = ""
    images: List[ImgInfo] = dataclasses.field(default_factory=list)
    author: VideoAuthor = dataclasses.field(default_factory=VideoAuthor)


class BaseParser(ABC):
    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        return {
            "User-Agent": fake_useragent.UserAgent(os="iOS").random,
        }

    @abstractmethod
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        pass

    @abstractmethod
    async def parse_video_id(self, video_id: str) -> VideoInfo:
        pass
