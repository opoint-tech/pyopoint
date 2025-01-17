from typing import Literal, Required, TypedDict


class MediaType(TypedDict):
    clip: bool
    hastext: bool
    haslogo: bool
    text: Literal["WEB"] | Literal["PRINT"]  # TODO: Track down all options here


class Language(TypedDict):
    encoding: str
    text: str


class LocalTime(TypedDict):
    GMT: int
    text: str


class TextObject(TypedDict):
    text: str


class SiteRank(TypedDict):
    rank_global: int
    rank_country: int


class FirstSource(TypedDict):
    id: int
    name: str
    url: str
    sitename: str
    siteurl: str


class SimilarWeb(TypedDict):
    domain: str


class Content(TypedDict):
    matches: bool
    text: str


class ArticleImage(TypedDict):
    url: str


class ArticleImages(TypedDict):
    count: int
    articleimage: list[ArticleImage]


class Topic(TypedDict):
    id: int
    linktype_max: int
    linktype_now: int
    metacat: int
    metacat_level: int
    text: str


class InternalSearchReply(TypedDict):
    id_site: int
    id_article: int
    text: str


class Article(TypedDict):
    id_site: int
    id_article: int
    position: int
    equalgroup: int
    id_delivery: int
    countrycode: str
    countryname: str
    similarweb: SimilarWeb
    site_rank: SiteRank
    unix_timestamp: int
    mediatype: MediaType
    curculation: int
    stimestamp: int
    stimestamp_index: int
    internal_search_reply: InternalSearchReply
    local_time: LocalTime
    local_rfc822_time: TextObject
    distribute_conditions: str
    content_protected: Literal[0] | Literal[1]
    language: Language
    word_count: int
    first_source: FirstSource
    header: Content
    sumnmary: Content
    body: Content
    articleimages: ArticleImages
    caption: TextObject
    quotes: list[str]  # TODO: Check
    url: str
    orig_url: str
    url_common: str
    topics: list[Topic]
    author: str
    screenshots: list[str]  # TODO: Check


class SearchResult(TypedDict, total=False):
    documents: Required[int]
    expected_rate: float
    first_timestamp: int
    last_timestamp: int
    generated_timestamp: int
    search_start: Required[int]
    context: str
    count: int
    cacheage: int  # TODO: Check
    cputime: int
    host: str
    compiledate: str
    branch: str
    notimeout: bool
    currency: str
    document: list[Article]


class FeedResponse(TypedDict):
    searchresult: SearchResult
