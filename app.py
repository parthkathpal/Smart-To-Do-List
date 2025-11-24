from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from config import Config
from models import db, Task
from datetime import datetime
import threading, time

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()

    def reminder_checker():
        with app.app_context():
            while True:
                now = datetime.utcnow()
                due = Task.query.filter(
                    Task.reminder_at != None,
                    Task.reminder_at <= now,
                    Task.completed == False,
                    Task.reminder_sent == False
                ).all()
                for t in due:
                    t.reminder_sent = True
                    db.session.add(t)
                if due:
                    db.session.commit()
                time.sleep(15)

    threading.Thread(target=reminder_checker, daemon=True).start()

    @app.route('/')
    def index():
        q = request.args.get('q','').strip()
        if q:
            tasks = Task.query.filter(Task.title.contains(q) | Task.description.contains(q)).all()
        else:
            tasks = Task.query.all()
        return render_template('index.html', tasks=tasks, q=q)

    @app.route('/task/create', methods=['GET','POST'])
    def create_task():
        if request.method=='POST':
            title=request.form['title']
            desc=request.form.get('description','')
            reminder=request.form.get('reminder','')
            r=None
            if reminder:
                try: r=datetime.fromisoformat(reminder)
                except: r=None
            t=Task(title=title, description=desc, reminder_at=r)
            db.session.add(t); db.session.commit()
            return redirect(url_for('index'))
        return render_template('create_task.html')

    @app.route('/task/<int:id>/edit', methods=['GET','POST'])
    def edit_task(id):
        t=Task.query.get_or_404(id)
        if request.method=='POST':
            t.title=request.form['title']
            t.description=request.form.get('description','')
            reminder=request.form.get('reminder','')
            if reminder:
                try: t.reminder_at=datetime.fromisoformat(reminder)
                except: t.reminder_at=None
            t.completed = 'completed' in request.form
            db.session.commit()
            return redirect(url_for('index'))
        return render_template('edit_task.html', task=t)

    @app.route('/task/<int:id>')
    def view_task(id):
        return render_template('view_task.html', task=Task.query.get_or_404(id))

    @app.route('/task/<int:id>/delete', methods=['POST'])
    def delete_task(id):
        t=Task.query.get_or_404(id)
        db.session.delete(t); db.session.commit()
        return redirect(url_for('index'))

    @app.route('/api/notifications')
    def notif():
        tasks=Task.query.filter_by(reminder_sent=True, reminder_seen=False).all()
        return jsonify([{'id':t.id,'title':t.title} for t in tasks])

    @app.route('/api/notifications/ack', methods=['POST'])
    def ack():
        data=request.get_json() or {}
        ids=data.get('ids',[])
        for i in ids:
            t=Task.query.get(i)
            if t:
                t.reminder_seen=True
        db.session.commit()
        return jsonify({'ok':True})

    return app

if __name__=='__main__':
    create_app().run(debug=True)
