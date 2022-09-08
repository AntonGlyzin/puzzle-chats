from django.contrib import admin
from genie.models import UserTemplate, Holidays, PicsHolidays,\
                        TextHolidays, audioHolidays
from django.utils.safestring import mark_safe


@admin.register(UserTemplate)
class UserTemplateAdmin(admin.ModelAdmin):
    list_display = ('username', 'linkname', 'time_create', 'sex', 'active')
    list_display_links = ('username', 'linkname')
    list_editable = ('active',)
    readonly_fields = ('id_user', 'time_create', 'linkname',)
    search_fields = ('username',)
    list_filter = ('active',)
    fieldsets = (
        (None, {
           'fields': ('id_user','username', 'linkname', 'sex', 'content', 'time_create',  )
        }),
        ('День рождение', {
            'fields': ('day_user', 'month_user'),
        }),
        (None, {
           'fields': ('active', )
        }),
    )

@admin.register(Holidays)
class HolidaysAdmin(admin.ModelAdmin):
    list_display = ('day', 'month', 'description', 'type_holiday')
    list_editable = ('type_holiday',)
    list_display_links = ('description', 'day', 'month')
    search_fields = ('description', 'day')
    list_filter = ('month',)
    ordering = ('month','day',)
    
    
@admin.register(PicsHolidays)
class PicsHolidaysAdmin(admin.ModelAdmin):
    list_display = ('get_html_photo', 'photo', 'for_cont','holidays', )
    list_display_links = ('get_html_photo', 'photo', 'holidays', )
    search_fields = ('holidays', )
    list_filter = ('holidays', )
    readonly_fields = ('get_html_photo', 'link', 'photo')
    list_per_page = 15
    def get_html_photo(self, object):
        if object.link:
            return mark_safe(f"<img src='{object.link}' width=113>")
    get_html_photo.short_description = "Фото к празднику"
    
    
@admin.register(TextHolidays)
class TextHolidaysAdmin(admin.ModelAdmin):
    list_display = ('get_description', 'for_cont','holidays', )
    list_display_links = ('get_description', 'holidays', )
    search_fields = ('holidays', )
    list_filter = ('holidays', )
    list_per_page = 25
    def get_description(self, obj):
        return obj.content[:70]+'...'
    get_description.short_description = "Поздравление"
    
@admin.register(audioHolidays)
class AudioHolidaysAdmin(admin.ModelAdmin):
    list_display = ('get_html_audio', 'file_id', 'for_cont','holidays', )
    list_display_links = ('get_html_audio', 'file_id', 'holidays', )
    search_fields = ('holidays', )
    readonly_fields = ('get_html_audio', 'link', 'file_id')
    list_filter = ('holidays', )
    list_per_page = 25
    def get_html_audio(self, object):
        if object.link:
            try:
                return mark_safe(f"<audio controls src='{object.link}' ></audio>")
            except BaseException as err:
                print(err)
    get_html_audio.short_description = "Музыка к празднику"