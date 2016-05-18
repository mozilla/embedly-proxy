from urlparse import urlsplit

from marshmallow import Schema, fields
from publicsuffix import PublicSuffixList


PSL = PublicSuffixList()


class AuthorSchema(Schema):
    url = fields.Url(allow_none=True)
    name = fields.Str(allow_none=True)


class AppLinkSchema(Schema):
    namespace = fields.Str(allow_none=True)
    package = fields.Str(allow_none=True)
    path = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)


class EntitySchema(Schema):
    count = fields.Int(allow_none=True)
    name = fields.Str(allow_none=True)


class KeywordSchema(Schema):
    score = fields.Int(allow_none=True)
    name = fields.Str(allow_none=True)


class ColorSchema(Schema):
    color = fields.List(fields.Int)
    weight = fields.Float(allow_none=True)


class MediaSchema(Schema):
    author_name = fields.Str(allow_none=True)
    author_url = fields.Url(allow_none=True)
    cache_age = fields.Int(allow_none=True)
    description = fields.Str(allow_none=True)
    provider_name = fields.Str(allow_none=True)
    provider_url = fields.Url(allow_none=True)
    thumbnail_height = fields.Int(allow_none=True)
    thumbnail_url = fields.Url(allow_none=True)
    thumbnail_width = fields.Int(allow_none=True)
    title = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)
    version = fields.Str(allow_none=True)


class ImageSchema(Schema):
    caption = fields.Str(allow_none=True)
    colors = fields.Nested(ColorSchema, many=True)
    entropy = fields.Float(allow_none=True)
    height = fields.Int(allow_none=True)
    size = fields.Int(allow_none=True)
    url = fields.Url(allow_none=True)
    width = fields.Int(allow_none=True)


class EmbedlyURLSchema(Schema):
    app_links = fields.Nested(AppLinkSchema, many=True)
    authors = fields.Nested(AuthorSchema, many=True)
    cache_age = fields.Int(allow_none=True)
    content = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    embeds = fields.Nested(MediaSchema, many=True)
    entities = fields.Nested(EntitySchema, many=True)
    favicon_colors = fields.Nested(ColorSchema, many=True, allow_none=True)
    favicon_url = fields.Url(allow_none=True)
    images = fields.Nested(ImageSchema, many=True)
    keywords = fields.Nested(KeywordSchema, many=True)
    language = fields.Str(allow_none=True)
    lead = fields.Str(allow_none=True)
    media = fields.Nested(MediaSchema)
    offset = fields.Int(allow_none=True)
    original_url = fields.Url(allow_none=True)
    provider_display = fields.Str(allow_none=True)
    provider_name = fields.Str(allow_none=True)
    provider_url = fields.Url(allow_none=True)
    published = fields.Int(allow_none=True)
    related = fields.Nested(MediaSchema, many=True)
    safe = fields.Bool(allow_none=True)
    title = fields.Str(allow_none=True)
    type = fields.Str(allow_none=True)
    url = fields.Url(allow_none=True)

    def __init__(self, blocked_domains, *args, **kwargs):
        self.blocked_domains = blocked_domains
        super(EmbedlyURLSchema, self).__init__(*args, **kwargs)

    def load(self, data):
        validated = super(EmbedlyURLSchema, self).load(data)

        def get_domain(url):
            return PSL.get_public_suffix(urlsplit(url).netloc)

        original_domain = get_domain(validated.data.get('original_url', ''))

        disallowed_domains = [
            domain for domain in self.blocked_domains
            if domain != original_domain
        ]

        validated.data['images'] = [
            image for image in validated.data.get('images', [])
            if get_domain(image.get('url', '')) not in disallowed_domains
        ]

        return validated
