from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import Item
from .serializers import ItemSerializer
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.core.exceptions import ValidationError
import os
from pathlib import Path
from rest_framework.decorators import action
import shutil
from rest_framework.pagination import PageNumberPagination

class ItemPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100
    limit_query_param = 'limit'

    def get_page_size(self, request):
        limit = request.query_params.get(self.limit_query_param, None)
        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = self.page_size
            if limit > self.max_page_size:
                return self.max_page_size 
            return limit
        return self.page_size


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    @transaction.atomic
    def perform_create(self, serializer):
        """
            Creation of an item folder. Validates the item and creates the necessary folder structure.
        """
        item = serializer.save()
        try:
            item.clean()
        except ValidationError as e:
            raise Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        item_path = item.get_full_path()
        if item.is_folder():
            os.makedirs(item_path, exist_ok=True)
        else:
            if item.parent and item.parent.is_folder():
                parent_folder_path = item.parent.get_full_path()
                if item.file:
                    item.file.name = os.path.join(parent_folder_path, item.file.name)
                    item.save()
            else:
                raise ValidationError("Files must have a valid folder as parent.")

    @transaction.atomic
    def perform_update(self, serializer):
        """
            Updating an item, ensuring changes to file paths or folder paths are properly applied in the filesystem.
        """
        item = self.get_object()
        old_item_path = item.get_full_path()
        old_name = item.name
        item_type = item.type
        updated_item = serializer.save()
        try:
            if item_type == Item.FILE:
                old_extension = Path(old_name).suffix
                new_name = updated_item.name
                new_extension = Path(new_name).suffix
                if not new_extension:
                    new_name = f"{new_name}{old_extension}"
                    updated_item.name = new_name
                    updated_item.save()
                new_item_path = updated_item.get_full_path()
                if os.path.exists(old_item_path):
                    os.rename(old_item_path, new_item_path)
                else:
                    raise ValidationError(f"Old file path does not exist: {old_item_path}")
            elif item_type == Item.FOLDER:
                new_item_path = updated_item.get_full_path()
                if old_item_path != new_item_path and os.path.exists(old_item_path):
                    os.rename(old_item_path, new_item_path)
        except Exception as e:
            raise ValidationError(f"Error renaming or updating item: {e}")
        return updated_item
    
    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='create-file')
    def create_file(self, request):
        """
            Creation and upload of a file within a specified folder.
            Validates the file and updates the database with file information.
        """
        parent_id = request.data.get('parent_id')
        file_name = request.data.get('name')
        uploaded_file = request.FILES.get('file')
        if not parent_id or not file_name:
            return Response({"error": "'parent_id' and 'name' are required."}, status=status.HTTP_400_BAD_REQUEST)
        if not uploaded_file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            parent_item = Item.objects.get(id=parent_id)
            if parent_item.type != Item.FOLDER:
                return Response({"error": "The parent ID must refer to a folder."}, status=status.HTTP_400_BAD_REQUEST)
            file_extension = os.path.splitext(uploaded_file.name)[1]  # Includes the dot (e.g., '.png')
            if not file_extension:
                return Response({"error": "Uploaded file must have a valid extension."}, status=status.HTTP_400_BAD_REQUEST)
            full_file_name = f"{file_name}{file_extension}"
            folder_path = parent_item.get_full_path()
            os.makedirs(folder_path, exist_ok=True)
            fs = FileSystemStorage(location=folder_path)
            saved_filename = fs.save(full_file_name, uploaded_file)
            file_item = Item.objects.create(
                name=full_file_name,
                type=Item.FILE,
                parent=parent_item,
                file = uploaded_file,
                file_path=os.path.join('files', parent_item.get_full_path(), saved_filename)
            )
            return Response(
                {
                    "message": "File uploaded successfully.",
                    "file_path": file_item.file_path,
                },
                status=status.HTTP_201_CREATED,
            )
        except Item.DoesNotExist:
            return Response({"error": "Parent folder not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='move-item')
    def move_item(self, request):
        """
            Move a file or folder from one location to another folder.
        """
        item_id = request.data.get('item_id')
        new_parent_id = request.data.get('new_parent_id')
        if not item_id or not new_parent_id:
            return Response({"error": "'item_id' and 'new_parent_id' are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = Item.objects.get(id=item_id)
            new_parent = Item.objects.get(id=new_parent_id)
            if new_parent.type != Item.FOLDER:
                return Response({"error": "The new parent must be a folder."}, status=status.HTTP_400_BAD_REQUEST)
            if item.type == Item.FILE:
                old_item_path = item.get_full_path()
                new_item_path = os.path.join(new_parent.get_full_path(), item.name)
                if os.path.exists(new_item_path):
                    return Response({"error": "A file with the same name already exists in the destination folder."}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                if not os.path.exists(old_item_path):
                    return Response({"error": "The source file does not exist."}, status=status.HTTP_404_NOT_FOUND)
                item.parent = new_parent
                item.file_path = os.path.join('files', new_item_path)  # Update the path in the database
                item.save()
                shutil.move(old_item_path, new_item_path)
            elif item.type == Item.FOLDER:
                old_folder_path = item.get_full_path()
                new_folder_path = os.path.join(new_parent.get_full_path(), item.name)
                if os.path.exists(new_folder_path):
                    return Response({"error": "A folder with the same name already exists in the destination folder."}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                if not os.path.exists(old_folder_path):
                    return Response({"error": "The source folder does not exist."}, status=status.HTTP_404_NOT_FOUND)
                shutil.move(old_folder_path, new_folder_path)
                item.parent = new_parent
                item.save()
            else:
                return Response({"error": "Item must be either a file or a folder."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Item moved successfully."}, status=status.HTTP_200_OK)
        except Item.DoesNotExist:
            return Response({"error": "Item or new parent folder not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @transaction.atomic
    def perform_destroy(self, instance):
        """
            Deletion of a file or folder. Removes associated filesystem entries and database records.
        """
        item_id = instance.id
        if not item_id:
            return Response({"error": "'id' is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            item_queryset = Item.objects.get(id=item_id)
            item_path = item_queryset.get_full_path()
            if item_queryset.type == Item.FOLDER:
                shutil.rmtree(item_path)
                Item.objects.filter(parent=item_queryset).delete()
                item_queryset.delete()
            elif item_queryset.type == Item.FILE:
                if os.path.exists(item_path):
                    Item.objects.filter(id=item_queryset.id).delete()
                    os.remove(item_path)
                else:
                    return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Folder and its contents deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Item.DoesNotExist:
            return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    @action(detail=False, methods=['get'], url_path='list-contents')
    def list_contents(self, request):
        """
            Retrieve and list the contents of a folder. Supports searching, filtering, and pagination.
        """
        try:
            pk = request.query_params.get('id', None)
            search_term = request.query_params.get('search', None)
            ordering_param = request.query_params.get('ordering', None)
            if pk:
                folder = Item.objects.filter(id=pk, type=Item.FOLDER).first()
                if not folder:
                    return Response({"error": "Folder not found or invalid folder id."}, status=status.HTTP_404_NOT_FOUND)
                queryset = Item.objects.filter(parent_id=pk)
            else:
                queryset = Item.objects.all()
            if search_term:
                queryset = queryset.filter(name__icontains=search_term)
            if ordering_param:
                queryset = queryset.order_by(ordering_param)
            paginator = ItemPagination()
            paginated_items = paginator.paginate_queryset(queryset, request)
            serializer = ItemSerializer(paginated_items, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
