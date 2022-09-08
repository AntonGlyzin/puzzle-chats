from django.urls import path, re_path, include
from .views import PortfolioViewSet, BlogViewSet, PageViewSet, \
                        CreateComment, UpdateComment, getMenu,\
                        EventViewList, ListMeComment, \
                        ProfileForm, getSkills, addSkill, CreatePostPortfolio,\
                        getTypeContent, WorkedMePosts, GetContentForEdit,\
                        SetRaiting, SetLikes, AddEditEventView, getMyPics,\
                        dowloadMyPics, deleteMyPic, setMyPicAva, GetDocResum,\
                        UserResume, SetView, UserFollowersView, FollowPostsMe,\
                        FollowEventsMe, UploadFileToPost
from .router import CustomReadOnlyRouter
from django.contrib.sitemaps import views

router = CustomReadOnlyRouter()
router.register('portfolio', PortfolioViewSet, basename='portfolio')
router.register('blog', BlogViewSet, basename='blog')
urlpatterns = router.urls

urlpatterns += [
    path('page/<slug:slug>', PageViewSet.as_view({'get':'retrieve'}), name='page-detail'),
    path('comment/create', CreateComment.as_view()),
    path('comment/delete/<int:id>', UpdateComment.as_view({'get':'update'})),
    path('getmenu', getMenu.as_view()),
    path('events', EventViewList.as_view({'get':'list'})),
    path('detail/user/comments', ListMeComment.as_view({'get':'list'})),
    re_path(r'card/user/(?P<user__username>\w+)', ProfileForm.as_view({'get':'retrieve'})),
    path('detail/user/allskills', getSkills.as_view()),
    path('detail/user/addskill', addSkill.as_view()),
    path('detail/user/post/create', CreatePostPortfolio.as_view({'post':'create'})),
    path('detail/user/post/delete', CreatePostPortfolio.as_view({'post':'destroy'})),
    path('detail/user/post/update', CreatePostPortfolio.as_view({'post':'partial_update'})),
    path('detail/user/typecontent', getTypeContent.as_view()),
    path('detail/user/posts', WorkedMePosts.as_view({'get':'list'})),
    path('detail/user/post/content/<int:id>', GetContentForEdit.as_view()),
    path('post/raiting/set', SetRaiting.as_view()),
    path('comment/like/set', SetLikes.as_view({'post':'create'})),
    path('comment/like/delete', SetLikes.as_view({'post':'destroy'})),
    path('events/user/addevent', AddEditEventView.as_view({'post': 'create'})),
    path('events/user/update/<int:id>', AddEditEventView.as_view({'put': 'partial_update'})),
    path('events/user/delete/<int:id>', AddEditEventView.as_view({'delete': 'destroy'})),
    path('detail/user/pics/list', getMyPics.as_view()),
    path('detail/user/pics/download', dowloadMyPics.as_view()),
    path('detail/user/pics/delete', deleteMyPic.as_view()),
    path('detail/user/pics/setava', setMyPicAva.as_view()),
    path('detail/user/getdoc', GetDocResum.as_view()),
    path('detail/user/resume/get', UserResume.as_view()),
    path('detail/user/resume/save', UserResume.as_view()),
    path('comment/view/set', SetView.as_view({'post':'create'})),
    path('detail/user/follower', UserFollowersView.as_view({'get': 'list',
                                                            'put': 'update'})),
    path('follow/posts/', include([
        path('events', FollowEventsMe.as_view({'get': 'list'})),
        path('portfolio', FollowPostsMe.as_view({'get': 'list'}), {'postfix': 'portfolio'}),
        path('blog', FollowPostsMe.as_view({'get': 'list'}), {'postfix': 'blog'})
    ])),
    path('detail/post/image/set', UploadFileToPost.as_view()),
    # path('detail/user/notify', NotifyList.as_view({'get': 'list'}))
]