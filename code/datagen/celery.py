from celery import Celery

app = Celery('datagen',
             broker='amqp://guest:guest@localhost:5672//',
             backend='redis://localhost:6379/0',
             include=['datagen.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
)

if __name__ == '__main__':
    app.start()
