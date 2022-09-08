from datetime import timedelta
BEAT_SCHEDULE = {
    'channel-tasks': [
        {
            'type': 'test.holidays',
            'message': None,
            'schedule': '0 3 * * *'
            # 'schedule': timedelta(seconds=5) 
        }
        # {
        #     'type': 'chat_force_test',
        #     'message': None,
        #     # 'schedule': timedelta(seconds=5)
        # },
    ]
}