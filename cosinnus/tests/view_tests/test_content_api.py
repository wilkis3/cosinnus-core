import re

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APILiveServerTestCase

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_MEMBER

User = get_user_model()

TEST_USER_DATA = {'username': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}


class MainContentViewTest(APILiveServerTestCase):
    # Not sure why, but setting available apps to installed apps fixes the database setup.
    # Without this the test database setup fails unable to create wagtail tables.
    available_apps = settings.INSTALLED_APPS

    @classmethod
    def setUpClass(cls):
        cache.clear()
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-content-main')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cache.clear()

    def setUp(self):
        cache.clear()
        super().setUp()
        site = Site.objects.first()
        site.domain = f'{self.host}:{self.server_thread.port}'
        site.save()
        self.domain = f'http://{site.domain}'
        # recreate portal, as objects created by migrations are droped by the TransactionTestCase teardown.
        CosinnusPortal.objects.get_or_create(
            id=1, defaults={'name': 'default portal', 'slug': 'default', 'public': True, 'site': site}
        )
        self.test_user = User.objects.create(**TEST_USER_DATA)
        self.test_user_profile = self.test_user.cosinnus_profile
        self.test_group = CosinnusSociety.objects.create(name='Test Group')
        self.test_group.memberships.create(user=self.test_user, status=MEMBERSHIP_MEMBER)

    def test_group_detail(self):
        """Basic test for accessing the group dashboard."""
        self.client.force_login(self.test_user)
        content_url = f'/group/{self.test_group.slug}/'
        response = self.client.get(self.api_url + f'?url={content_url}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status_code'], 200)
        self.assertEqual(response.data['resolved_url'], content_url)
        self.assertEqual(response.data['main_menu']['label'], self.test_group.name)
        self.assertEqual(response.data['sub_navigation']['top'][0]['label'], 'Microsite')
        self.assertIsNotNone(re.search(rf'<h2>\s*{self.test_group.name}\s*</h2>', response.data['content_html']))

    def test_personal_dashboard(self):
        """Basic test for accessing the personal dashboard."""
        self.client.force_login(self.test_user)
        content_url = '/dashboard/'
        response = self.client.get(self.api_url + f'?url={content_url}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status_code'], 200)
        self.assertEqual(response.data['resolved_url'], content_url)
        self.assertEqual(response.data['main_menu']['label'], 'Personal Dashboard')
        self.assertIn('<h2 class="headline mobile-hidden">News</h2>', response.data['content_html'])

    def test_template_processing(self):
        """TODO"""
        content_url = reverse('cosinnus:main-content-test')
        response = self.client.get(self.api_url + f'?url={content_url}')
        self.assertEqual(response.status_code, 200)

        # check response status
        self.assertEqual(response.data['status_code'], 200)
        self.assertEqual(response.data['resolved_url'], content_url)
        self.assertFalse(response.data['redirect'])

        # check meta
        self.assertEqual(response.data['meta'], '<meta charset="utf-8"/>')

        # check js
        self.assertEqual(response.data['js_vendor_urls'], [f'{self.domain}/static/js/vendor/test.js'])
        self.assertEqual(response.data['js_urls'], [f'{self.domain}/static/js/cosinnus.js'])
        self.assertEqual(response.data['script_constants'], 'var constant;')
        self.assertEqual(response.data['scripts'], 'var head_script;\nvar body_script;')

        # check css
        self.assertEqual(response.data['css_urls'], [f'{self.domain}/static/css/test.css'])
        self.assertEqual(response.data['styles'], '.test_style {}')

        # check html content
        self.assertEqual(
            response.data['content_html'].replace('\n', ''), '<div class="x-v3-container">  Test-Content  </div>'
        )

        # check footer
        self.assertEqual(response.data['footer_html'], 'Test-Footer')

        """
        # TODO
        'sub_navigation': None
        'main_menu': {
        """
