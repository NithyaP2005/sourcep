from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql.cursors
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'db': 'pet_adoption',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/pets')
def pets():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM pets WHERE status='available'"
            cursor.execute(sql)
            pets = cursor.fetchall()
    finally:
        connection.close()
    return render_template('pets.html', pets=pets)

@app.route('/pet/<int:pet_id>')
def pet_details(pet_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM pets WHERE id=%s"
            cursor.execute(sql, (pet_id,))
            pet = cursor.fetchone()

            if not pet:
                flash('Pet not found', 'error')
                return redirect(url_for('pets'))
    finally:
        connection.close()
    return render_template('pet_details.html', pet=pet)

@app.route('/adoption-process')
def adoption_process():
    return render_template('adoption_process.html')

@app.route('/success-stories')
def success_stories():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT pets.name as pet_name, pets.species, pets.breed, 
                   adoptions.adopter_name, adoptions.adoption_date 
            FROM adoptions 
            JOIN pets ON adoptions.pet_id = pets.id 
            WHERE adoptions.status='completed'
            ORDER BY adoptions.adoption_date DESC
            """
            cursor.execute(sql)
            stories = cursor.fetchall()
    finally:
        connection.close()
    return render_template('success_stories.html', stories=stories)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO contacts (name, email, phone, message) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (name, email, phone, message))
            connection.commit()
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            connection.rollback()
            flash('An error occurred. Please try again.', 'error')
        finally:
            connection.close()
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/adopt/<int:pet_id>', methods=['POST'])
def adopt(pet_id):
    if request.method == 'POST':
        adopter_name = request.form['name']
        adopter_email = request.form['email']
        adopter_phone = request.form['phone']
        adopter_address = request.form['address']
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Check if pet exists and is available
                sql = "SELECT * FROM pets WHERE id=%s AND status='available'"
                cursor.execute(sql, (pet_id,))
                pet = cursor.fetchone()
                
                if not pet:
                    flash('This pet is no longer available for adoption', 'error')
                    return redirect(url_for('pets'))
                
                # Create adoption record
                sql = """
                INSERT INTO adoptions 
                (pet_id, adopter_name, adopter_email, adopter_phone, adopter_address) 
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (pet_id, adopter_name, adopter_email, adopter_phone, adopter_address))
                
                # Update pet status
                sql = "UPDATE pets SET status='pending' WHERE id=%s"
                cursor.execute(sql, (pet_id,))
                
            connection.commit()
            flash('Your adoption application has been submitted successfully!', 'success')
        except Exception as e:
            connection.rollback()
            flash('An error occurred. Please try again.', 'error')
        finally:
            connection.close()
        
        return redirect(url_for('pet_details', pet_id=pet_id))

@app.route('/admin')
def admin():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get stats
            sql_pets = "SELECT COUNT(*) as total_pets FROM pets"
            cursor.execute(sql_pets)
            total_pets = cursor.fetchone()['total_pets']
            
            sql_adoptions = "SELECT COUNT(*) as total_adoptions FROM adoptions WHERE status='completed'"
            cursor.execute(sql_adoptions)
            total_adoptions = cursor.fetchone()['total_adoptions']
            
            sql_pending = "SELECT COUNT(*) as pending_adoptions FROM adoptions WHERE status='pending'"
            cursor.execute(sql_pending)
            pending_adoptions = cursor.fetchone()['pending_adoptions']
            
            # Get recent contacts
            sql_contacts = "SELECT * FROM contacts ORDER BY created_at DESC LIMIT 5"
            cursor.execute(sql_contacts)
            recent_contacts = cursor.fetchall()
            
            # Get pending adoptions
            sql_pending_apps = """
            SELECT adoptions.*, pets.name as pet_name, pets.species 
            FROM adoptions 
            JOIN pets ON adoptions.pet_id = pets.id 
            WHERE adoptions.status='pending'
            """
            cursor.execute(sql_pending_apps)
            pending_apps = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin.html', 
                         total_pets=total_pets,
                         total_adoptions=total_adoptions,
                         pending_adoptions=pending_adoptions,
                         recent_contacts=recent_contacts,
                         pending_apps=pending_apps)

@app.route('/admin/approve/<int:adoption_id>')
def approve_adoption(adoption_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get adoption record
            sql = "SELECT * FROM adoptions WHERE id=%s"
            cursor.execute(sql, (adoption_id,))
            adoption = cursor.fetchone()
            
            if not adoption:
                flash('Adoption record not found', 'error')
                return redirect(url_for('admin'))
            
            # Update adoption status
            sql = "UPDATE adoptions SET status='completed' WHERE id=%s"
            cursor.execute(sql, (adoption_id,))
            
            # Update pet status
            sql = "UPDATE pets SET status='adopted' WHERE id=%s"
            cursor.execute(sql, (adoption['pet_id'],))
            
        connection.commit()
        flash('Adoption approved successfully!', 'success')
    except Exception as e:
        connection.rollback()
        flash('An error occurred. Please try again.', 'error')
    finally:
        connection.close()
    
    return redirect(url_for('admin'))

@app.route('/admin/reject/<int:adoption_id>')
def reject_adoption(adoption_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get adoption record
            sql = "SELECT * FROM adoptions WHERE id=%s"
            cursor.execute(sql, (adoption_id,))
            adoption = cursor.fetchone()
            
            if not adoption:
                flash('Adoption record not found', 'error')
                return redirect(url_for('admin'))
            
            # Update adoption status
            sql = "UPDATE adoptions SET status='rejected' WHERE id=%s"
            cursor.execute(sql, (adoption_id,))
            
            # Update pet status
            sql = "UPDATE pets SET status='available' WHERE id=%s"
            cursor.execute(sql, (adoption['pet_id'],))
            
        connection.commit()
        flash('Adoption rejected successfully', 'success')
    except Exception as e:
        connection.rollback()
        flash('An error occurred. Please try again.', 'error')
    finally:
        connection.close()
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
