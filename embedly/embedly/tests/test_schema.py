from embedly.tests.base import AppTest
from embedly.schema import EmbedlyURLSchema


class TestEmbedlyURLSchema(AppTest):

    def setUp(self):
        super(TestEmbedlyURLSchema, self).setUp()
        self.schema = EmbedlyURLSchema(blocked_domains=['blockeddomain.com'])

    def get_test_image(self, **kwargs):
        test_image = {
            'entropy': 0.1,
            'height': 200,
            'size': 12345,
            'width': 200,
            'url': 'https://example.com/image.jpg',
        }
        test_image.update(kwargs)
        return test_image

    def test_validator_accepts_valid_data(self):
        validated = self.schema.load(self.test_data)
        self.assertEqual(validated.data, self.test_data)
        self.assertEqual(validated.errors, {})

    def test_validator_removes_images_with_blocked_domain_and_subdomains(self):
        blocked_image = self.get_test_image(
            url='https://blockeddomain.com/image.jpg')

        blocked_subdomain_image = self.get_test_image(
            url='https://subdomain.blockeddomain.com/image.jpg')

        allowed_image = self.get_test_image(
            url='https://alloweddomain.com/image.jpg')

        self.test_data['images'] = [
            blocked_image,
            blocked_subdomain_image,
            allowed_image,
        ]

        validated = self.schema.load(self.test_data)

        self.assertIn(allowed_image, validated.data['images'])
        self.assertNotIn(blocked_image, validated.data['images'])
        self.assertNotIn(blocked_subdomain_image, validated.data['images'])

    def test_validator_accepts_blocked_domains_for_same_url_domain(self):
        self.test_data['original_url'] = 'https://blockeddomain.com/beep/'

        blocked_image = self.get_test_image(
            url='https://blockeddomain.com/image.jpg')

        self.test_data['images'] = [
            blocked_image,
        ]

        validated = self.schema.load(self.test_data)

        self.assertIn(blocked_image, validated.data['images'])

    def test_validator_returns_only_largest_image(self):
        bigger_image = self.get_test_image(
            height=200, width=200, url='https://www.example.com/bigger.jpg')
        smaller_image = self.get_test_image(
            height=100, width=100, url='https://www.example.com/smaller.jpg')

        self.test_data['images'] = [
            smaller_image,
            bigger_image,
        ]

        validated = self.schema.load(self.test_data)

        self.assertEqual(len(validated.data['images']), 1)
        self.assertIn(bigger_image, validated.data['images'])
