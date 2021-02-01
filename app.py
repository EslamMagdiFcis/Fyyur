#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import dateutil.parser
import babel
from datetime import date, datetime
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import FlaskForm, form
from sqlalchemy.orm import lazyload
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='venue_shows', lazy=True)

    def __repr__(self):
        return f'<Venue ID: {self.id}, Name: {self.name}>'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(500))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    shows = db.relationship('Show', backref='artist_shows', lazy=True)

    def __repr__(self):
      return f'<Artist ID: {self.id}, Name: {self.name}>'


class Show(db.Model):
  __tablename__ = 'Show'
  id = db.Column(db.Integer, primary_key=True)
  start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)

  def __repr__(self):
    return f'<Show ID: {self.id}, Start Date: {self.start_date}, Artist: {self.artist_id}, Venue: {self.venue_id}>' 


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []

  veune_group_by_city_state = db.session.query(Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()

  for group in veune_group_by_city_state:
    city, state = group
    venues = Venue.query.filter_by(city=city, state=state).all()

    venues_list = [{'id':venue.id, 
                    'name': venue.name, 
                    'num_upcoming_shows': len(venue.shows)}
                    for venue in venues]

    item = {'city': city, 'state': state, 'venues': venues_list}

    data.append(item)

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  
  search_term = request.form.get('search_term', '')

  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()

  response = {
    'count': len(venues),
    'data': [{'id': venue.id,
              'name': venue.name,
              'num_upcoming_shows': len(venue.shows),
    } for venue in venues]
  }

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  def data_to_list(join_data):
    return [
            {'artist_id': artist_id,
             'artist_name': artist_name,
             'artist_image_link': artist_image_link,
             'start_time': str(start_time)
            } for start_time, artist_name, artist_id, artist_image_link in join_data]

  venue = Venue.query.get(venue_id)

  past_shows = db.session.query(Show.start_date,
                                Artist.name, 
                                Artist.id, 
                                Artist.image_link)\
                         .join(Show)\
                         .filter(Show.venue_id == venue_id, Show.start_date <= datetime.utcnow())\
                         .all()
  

  past_shows_list = data_to_list(past_shows)

  upcoming_shows = db.session.query(Show.start_date,Artist.name, 
                                    Artist.id, Artist.image_link)\
                             .join(Show)\
                             .filter(Show.venue_id == venue_id, Show.start_date > datetime.utcnow())\
                            .all()

  upcoming_shows_list = data_to_list(upcoming_shows)
  
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": str(venue.genres.replace('{', '').replace('}','').replace('"', '')).split(','),
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": past_shows_list,
    "past_shows_count": len(past_shows_list),
    "upcoming_shows": upcoming_shows_list,
    "upcoming_shows_count": len(upcoming_shows_list)
  }

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()

  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

  form = VenueForm(request.form)

  try:
    venue = Venue()
    form.populate_obj(venue)
    db.session.add(venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except ValueError as e:
    print(e)
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  venue = Venue.query.get(venue_id)

  try:
    db.session.delete(venue)
    db.session.commit()
  except ValueError as e:
    print(e)
    db.session.rollback()
  finally:
    db.session.close()
  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage

  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = db.session.query(Artist.id, Artist.name).all()

  data = [{'id': id, 'name': name} for id, name in artists]
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():

  search_term = request.form.get('search_term', '')

  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

  response = {
    "count": len(artists),
    "data": [{
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": len(artist.shows),
    } for artist in artists]
  }

  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  def data_to_list(join_data):
    return [{
     "venue_id": venue_id,
     "venue_name": venue_name,
     "venue_image_link": venue_image_link,
     "start_time": str(start_time)
  } for start_time, venue_name, venue_id, venue_image_link in join_data]

  artist = Artist.query.get(artist_id)

  past_shows = db.session.query(Show.start_date, Venue.name, 
                                Venue.id, Venue.image_link)\
                            .join(Show)\
                            .filter(Show.artist_id == artist_id, Show.start_date <= datetime.utcnow())\
                            .all()
  

  past_shows_list = data_to_list(past_shows)

  upcoming_shows = db.session.query(Show.start_date, Venue.name, 
                                    Venue.id, Venue.image_link)\
                             .join(Show)\
                             .filter(Show.artist_id == artist_id, Show.start_date > datetime.utcnow())\
                             .all()

  upcoming_shows_list = data_to_list(upcoming_shows)

  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": str(artist.genres.replace('{', '').replace('}','').replace('"', '')).split(','),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": past_shows_list,
    "past_shows_count": len(past_shows_list),
    "upcoming_shows": upcoming_shows_list,
    "upcoming_shows_count": len(upcoming_shows_list)
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get(artist_id)

  form.name.data = artist.name
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.image_link.data = artist.image_link
  form.facebook_link.data = artist.facebook_link
  form.genres.data = artist.genres
  form.website.data = artist.website
  form.seeking_venue.data = artist.seeking_venue
  form.seeking_description.data = artist.seeking_description

  artist_json = {
    "id": artist.id,
    "name": artist.name,
    "genres": str(artist.genres.replace('{', '').replace('}','').replace('"', '')).split(','),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }

  return render_template('forms/edit_artist.html', form=form, artist=artist_json)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  form = ArtistForm(request.form)
  artist = Artist.query.get(artist_id)

  try:
    form.populate_obj(artist)
    db.session.commit()
  except ValueError as e:
    print(e)
    db.session.rollback()
  finally:
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)

  form.name.data = venue.name
  form.address.data = venue.address
  form.city.data = venue.city
  form.state.data = venue.state
  form.phone.data = venue.phone
  form.facebook_link.data = venue.facebook_link
  form.image_link.data = venue.image_link
  form.genres.data = venue.genres
  form.website.data = venue.website
  form.seeking_talent.data = venue.seeking_talent
  form.seeking_description.data = venue.seeking_description
  

  venue_json = {
    "id": venue.id,
    "name": venue.name,
    "genres": str(venue.genres.replace('{', '').replace('}','').replace('"', '')).split(','),
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }

  return render_template('forms/edit_venue.html', form=form, venue=venue_json)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

  venue = Venue.query.get(venue_id)
  form = VenueForm(request.form)

  try:
    form.populate_obj(venue)
    db.session.commit()
  except ValueError as e:
    print(e)
    db.session.rollback()
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

  form = ArtistForm(request.form)

  try:
    artist = Artist()
    form.populate_obj(artist)
    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except ValueError as e:
    print(e)
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

  shows = Show.query.join(Venue, Artist)\
                    .add_columns(Venue.name, Artist.name, Artist.image_link)\
                    .all()

  data = [{"venue_id": show.venue_id,
           "venue_name": venue_name,
           "artist_id": show.artist_id,
           "artist_name": artist_name,
           "artist_image_link": artist_image_link,
           "start_time": str(show.start_date)} 
          for show, venue_name, artist_name, artist_image_link in shows]

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():

  form = ShowForm(request.form)

  try:
    show = Show()
    form.populate_obj(show)
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  except ValueError as e:
    print(e)
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
