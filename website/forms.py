from django import forms
from website.models import BlogPost
from ckeditor.widgets import CKEditorWidget

class BlogPostForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = BlogPost
        fields = ['title', 'cover_image', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter blog title here...',
                'style': 'border-radius: 8px;'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'style': 'border-radius: 8px;'
            }),
        }
