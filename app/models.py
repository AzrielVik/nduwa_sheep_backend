from . import db
from sqlalchemy.orm import relationship
from datetime import datetime, date

class Sheep(db.Model):
    __tablename__ = 'sheep'

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.String(50), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=False)  # Changed from age to dob
    gender = db.Column(db.String(10), nullable=False)
    pregnant = db.Column(db.Boolean, default=False)
    medical_records = db.Column(db.Text)
    image = db.Column(db.String(200))
    weight = db.Column(db.Float)
    breed = db.Column(db.String(50))
    is_lamb = db.Column(db.Boolean, default=False)
    weaning_weight = db.Column(db.Float, nullable=True)  # <-- Added this line

    # Parent relationships (using sheep.id as foreign key)
    mother_id = db.Column(db.Integer, db.ForeignKey('sheep.id'), nullable=True)
    father_id = db.Column(db.Integer, db.ForeignKey('sheep.id'), nullable=True)

    # Relationships
    mother = relationship(
        'Sheep', remote_side=[id],
        foreign_keys=[mother_id],
        backref='mother_children'
    )
    father = relationship(
        'Sheep', remote_side=[id],
        foreign_keys=[father_id],
        backref='father_children'
    )

    @property
    def age(self):
        """Calculated age in years based on dob"""
        if self.dob:
            today = date.today()
            return today.year - self.dob.year - (
                (today.month, today.day) < (self.dob.month, self.dob.day)
            )
        return None

    def __repr__(self):
        return f"<Sheep {self.tag_id}>"

class Lamb(db.Model):
    __tablename__ = 'lambs'

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.String(50), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=False)  # Lamb's own date of birth
    gender = db.Column(db.String(10), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    image = db.Column(db.String(200))
    
    weaning_weight = db.Column(db.Float)

    # Parent relationships (using sheep.tag_id for easy reference)
    mother_tag_id = db.Column(db.String(50), db.ForeignKey('sheep.tag_id'))
    father_tag_id = db.Column(db.String(50), db.ForeignKey('sheep.tag_id'))

    # Relationships
    mother = relationship('Sheep', foreign_keys=[mother_tag_id], backref='lambs_by_mother')
    father = relationship('Sheep', foreign_keys=[father_tag_id], backref='lambs_by_father')

    @property
    def age_days(self):
        """Age in days (useful for lambs)"""
        if self.dob:
            return (date.today() - self.dob).days
        return None

    def __repr__(self):
        return f"<Lamb {self.tag_id}>"
