from django.db import models
from django.conf import settings
import os
from django.core.exceptions import ValidationError

class Item(models.Model):
    FILE = 'file'
    FOLDER = 'folder'
    ITEM_TYPE_CHOICES = [
        (FOLDER, 'Folder'),
        (FILE, 'File'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subitems')
    file = models.FileField(upload_to='files/', null=True, blank=True)  # Used for files only
    file_path = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_full_path(self):
        """Returns the full item path in the filesystem, including parent folders."""
        path_parts = [self.name]
        parent = self.parent
        while parent:
            path_parts.append(parent.name)
            parent = parent.parent
        return os.path.join(settings.MEDIA_ROOT, *reversed(path_parts))

    def is_folder(self):
        """Returns True if this item is a folder, otherwise False."""
        return self.type == self.FOLDER
    
    def is_file(self):
        """Returns True if this item is a file, otherwise False."""
        return self.type == self.FILE

    def clean(self):
        """
        Custom validation for files and folders.
        Ensures that files have valid parent folders and prevents invalid parent-child relationships.
        """
        if self.type == self.FILE:
            if self.parent and not self.parent.is_folder():
                raise ValidationError("Files must have a valid folder as their parent.")
            if self.parent and self.parent.subitems.filter(name=self.name, type=self.FILE).exclude(id=self.id).exists():
                raise ValidationError("A file with this name already exists in the parent folder.")
        elif self.type == self.FOLDER:
            if self.parent and self.parent.subitems.filter(name=self.name, type=self.FOLDER).exclude(id=self.id).exists():
                raise ValidationError("A folder with this name already exists in the parent folder.")
        super().clean()
