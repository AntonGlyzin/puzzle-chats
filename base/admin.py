from django.contrib import admin
from base.models import Profile, MySkils, ImagesLink
from django.utils.safestring import mark_safe

@admin.register(MySkils)
class MySkilsAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', )
    list_display_links = ('name', 'slug', )
    ist_filter = ('name', )
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name', 'slug')
    
# Register your models here.
@admin.register(ImagesLink)
class ImagesLinkAdmin(admin.ModelAdmin):
    list_display = ('get_html_photo', 'link', )
    list_display_links = ('get_html_photo', 'link', )
    readonly_fields = ('get_html_photo', 'link')
    def get_html_photo(self, object):
        if object.link:
            return mark_safe(f"<img src='{object.link}' width=113>")
    def add_view(self,request,extra_content=None):
         return super(ImagesLinkAdmin,self).add_view(request)
    def change_view(self, request, object_id, extra_context=None):
        self.exclude = ('name',)
        return super(ImagesLinkAdmin, self).change_view(request, object_id)
    get_html_photo.short_description = "Миниатюра"
    
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_name_user', 'get_html_photo', 'get_staff', 'get_active', 'type_app']
    list_filter = ('user__is_staff', 'type_app')
    list_editable = ('type_app', )
    readonly_fields = ('photo_user', )
    def get_name_user(self, object):
        return object.user.get_full_name()
    def get_staff(self, object):
        if object.user.is_staff:
           return  mark_safe('<img src="/static/admin/img/icon-yes.svg" alt="True">')
        else:
            return  mark_safe('<img src="/static/admin/img/icon-no.svg" alt="False">')
    def get_active(self, object):
        if object.user.is_active:
           return  mark_safe('<img src="/static/admin/img/icon-yes.svg" alt="True">')
        else:
            return  mark_safe('<img src="/static/admin/img/icon-no.svg" alt="False">')
    def get_html_photo(self, object):
        if object.photo:
            # ava = object.preview['avatar'].url
            ava = object.photo
            return mark_safe(f"<img src='{ava}' width=70>")
    get_html_photo.short_description = "Миниатюра"
    get_staff.short_description = "Доступ к админке"
    get_active.short_description = "Активен"
    get_name_user.short_description = 'Имя и Фамилия'