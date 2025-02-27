from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class HiddenLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    cover_text = db.Column(db.String(200), nullable=False)
    hidden_code = db.Column(db.String(1000), nullable=False)

    def __repr__(self):
        return f"<HiddenLink {self.id}>"