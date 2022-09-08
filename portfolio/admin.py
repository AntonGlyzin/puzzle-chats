from django.contrib import admin
from django.utils.safestring import mark_safe
from portfolio.models import WorkPost, Comment, \
                        TimeLine, Raiting, UserFollowers
from martor.widgets import AdminMartorWidget
from django.db import models

class CommentInline(admin.TabularInline):
    model = Comment
    fields = ('name', 'body', 'active')
    readonly_fields = ('name', 'body')
    

@admin.register(WorkPost)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'get_html_photo', 'type_content', 'get_views', 'date_created', 'is_published')
    list_display_links = ('get_html_photo', 'title', 'type_content')
    search_fields = ('title', 'author__username')
    list_filter = ('is_published', 'type_content')
    readonly_fields = ('get_html_photo', 'date_update', 'link')
    list_editable = ('is_published',)
    list_per_page = 15
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CommentInline]
    save_on_top = True
    def get_views(self, object):
        return len(object.viewers['ip'])
    def get_html_photo(self, object):
        if object.link:
            return mark_safe(f"<img src='{object.link}' width=113>")
    get_views.short_description = 'Просмотров'    
    get_html_photo.short_description = "Миниатюра"

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip', 'project', 'get_content', 'active')
    list_display_links = ('name', 'get_content', 'project')
    readonly_fields = ('ip', 'sess', )
    search_fields = ('project__title', 'user__user__username', 'body')
    list_editable = ('active',)
    list_filter = ('active', )
    exclude = ('child',)
    formfield_overrides = {
        models.TextField: {'widget': AdminMartorWidget},
    }
    save_on_top = True
    list_per_page = 20
    def get_content(self, object):
        if object.body:
            return object.body[:70]
        
    
@admin.register(TimeLine)
class TimeLineAdmin(admin.ModelAdmin):
    list_display = ('project', 'date_created', 'get_tranc_content', )
    list_display_links = ('project','date_created', 'get_tranc_content', )
    list_filter = ('date_created',)
    search_fields = ('project__title', )
    inlines = [CommentInline]
    save_on_top = True
    def get_tranc_content(self, object):
        return object.content[:70]
    get_tranc_content.short_description = "Контент"
    
@admin.register(Raiting)
class RaitingAdminModel(admin.ModelAdmin):
    list_display = ('project', 'user', 'num_rait', )
    list_display_links = ('project', 'user', 'num_rait', )
    list_filter = ('num_rait', )
    list_per_page = 15

@admin.register(UserFollowers)
class UserFollowersAdmin(admin.ModelAdmin):
    list_display = ('user',)
    list_display_links = ('user', )
    search_fields = ('user', )
    list_per_page = 30