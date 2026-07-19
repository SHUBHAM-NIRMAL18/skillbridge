from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from website.models import BlogPost

User = get_user_model()

class BlogPostTests(TestCase):
    def setUp(self):
        # Create users
        self.author = User.objects.create_user(
            username="author@example.com",
            email="author@example.com",
            password="testpassword",
            role="candidate"
        )
        self.other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpassword",
            role="candidate"
        )
        
        # Create blog post (unverified by default)
        self.blog = BlogPost.objects.create(
            author=self.author,
            title="My First Blog Post",
            content="<p>This is the content of my first blog post.</p>"
        )

    def test_blog_slug_generation(self):
        self.assertIsNotNone(self.blog.slug)
        self.assertEqual(self.blog.slug, "my-first-blog-post")

    def test_public_blog_list_only_shows_verified(self):
        # Unverified post should not show
        response = self.client.get(reverse('website:blog_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.blog.title)
        
        # Verify it
        self.blog.is_verified = True
        self.blog.save()
        
        # Verified post should show
        response = self.client.get(reverse('website:blog_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.blog.title)

    def test_blog_detail_access_permissions(self):
        blog_detail_url = reverse('website:blog_detail', kwargs={'slug': self.blog.slug})
        
        # Unauthenticated users cannot view unverified posts
        response = self.client.get(blog_detail_url)
        self.assertEqual(response.status_code, 302) # Redirect to blog list
        
        # Other authenticated users cannot view unverified posts
        self.client.login(username="other@example.com", password="testpassword")
        response = self.client.get(blog_detail_url)
        self.assertEqual(response.status_code, 302)
        
        # Author can view unverified posts
        self.client.login(username="author@example.com", password="testpassword")
        response = self.client.get(blog_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.blog.title)
        
        # When verified, everyone can view it
        self.blog.is_verified = True
        self.blog.save()
        self.client.logout()
        response = self.client.get(blog_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.blog.title)

    def test_blog_edit_resets_verification_and_requires_author(self):
        blog_edit_url = reverse('website:blog_edit', kwargs={'slug': self.blog.slug})
        
        # Verify post first
        self.blog.is_verified = True
        self.blog.save()
        
        # Other user cannot edit
        self.client.login(username="other@example.com", password="testpassword")
        response = self.client.get(blog_edit_url)
        self.assertEqual(response.status_code, 302) # Redirect
        
        # Author can edit
        self.client.login(username="author@example.com", password="testpassword")
        response = self.client.post(blog_edit_url, {
            'title': 'My Edited Blog Post',
            'content': '<p>New content</p>'
        })
        self.assertEqual(response.status_code, 302) # Success redirect to my-blogs
        
        # Reload blog post
        self.blog.refresh_from_db()
        self.assertEqual(self.blog.title, 'My Edited Blog Post')
        self.assertFalse(self.blog.is_verified) # Verification status should reset to False
