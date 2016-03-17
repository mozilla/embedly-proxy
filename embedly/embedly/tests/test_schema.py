from embedly.tests.base import AppTest
from embedly.schema import EmbedlyURLSchema


class TestEmbedlyURLSchema(AppTest):

    def setUp(self):
        super(TestEmbedlyURLSchema, self).setUp()
        self.schema = EmbedlyURLSchema()

    def test_validator_accepts_valid_data(self):
        with self.app.app_context():
            validated = self.schema.load(self.test_data)
            self.assertEqual(validated.data, self.test_data)
            self.assertEqual(validated.errors, {})

    def test_validator_removes_images_with_blocked_domain_and_subdomains(self):
        self.app.config['BLOCKED_DOMAINS'] = ['blockeddomain.com']

        blocked_image = {'url': 'https://blockeddomain.com/image.jpg'}
        blocked_subdomain_image = {
            'url': 'https://subdomain.blockeddomain.com/image.jpg',
        }
        allowed_image = {'url': 'https://alloweddomain.com/image.jpg'}

        self.test_data['images'] = [
            blocked_image,
            blocked_subdomain_image,
            allowed_image,
        ]

        with self.app.app_context():
            validated = self.schema.load(self.test_data)

        self.assertIn(allowed_image, validated.data['images'])
        self.assertNotIn(blocked_image, validated.data['images'])
        self.assertNotIn(blocked_subdomain_image, validated.data['images'])

    def test_valdiator_accepts_blocked_domains_for_same_url_domain(self):
        self.app.config['BLOCKED_DOMAINS'] = ['blockeddomain.com']

        self.test_data['original_url'] = 'https://blockeddomain.com/beep/'

        blocked_image = {'url': 'https://blockeddomain.com/image.jpg'}
        allowed_image = {'url': 'https://alloweddomain.com/image.jpg'}

        self.test_data['images'] = [
            blocked_image,
            allowed_image,
        ]

        with self.app.app_context():
            validated = self.schema.load(self.test_data)

        self.assertIn(allowed_image, validated.data['images'])
        self.assertIn(blocked_image, validated.data['images'])
