from pydantic import HttpUrl, BaseModel


class ImportUrlIn( BaseModel):
    url: HttpUrl