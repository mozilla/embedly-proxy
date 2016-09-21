from urlparse import urlsplit

from marshmallow import Schema, fields
from publicsuffix import PublicSuffixList


PSL = PublicSuffixList()


class ImageSchema(Schema):
    height = fields.Int(allow_none=True)
    url = fields.Url(allow_none=True)
    width = fields.Int(allow_none=True)


class EmbedlyURLSchema(Schema):
    description = fields.Str(allow_none=True)
    favicon_url = fields.Url(allow_none=True)
    images = fields.Nested(ImageSchema, many=True)
    original_url = fields.Url(allow_none=True)
    provider_display = fields.Str(allow_none=True)
    provider_name = fields.Str(allow_none=True)
    provider_url = fields.Url(allow_none=True)
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

        def cmp_images(img_a, img_b):
            return cmp(
                img_b['width'] * img_b['height'],
                img_a['width'] * img_a['height'],
            )

        sorted_images = sorted(validated.data['images'], cmp=cmp_images)
        validated.data['images'] = sorted_images[:1]

        return validated
