# This file contains an example Flask-User application.
# To keep the example simple, we are applying some unusual techniques:
# - Placing everything in one file
# - Using class-based configuration (instead of file-based configuration)
# - Using string-based templates (instead of file-based templates)

import datetime
from time import gmtime, strftime
from flask import Flask, request, render_template_string, render_template,redirect, session
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_user import current_user, login_required, roles_required, UserManager, UserMixin
import flask_login
import sqlite3 as sql
from flask_login import LoginManager, login_user
from flask_bcrypt import Bcrypt
from sqlalchemy.sql import table,column,select
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy import inspect

# Class-based application configuration


class ConfigClass(object):
    """ Flask application config """

    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///basic_app.sqlite'    # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False    # Avoids SQLAlchemy warning

    # Flask-Mail SMTP server settings
    # #USER_ENABLE_EMAIL=True ise bu ayarları yapın. Google güvenlik ayarları bu işlemi yapmanıza izin vermeyebilir.
    # Detaylı bilgiyi https://support.google.com/accounts/answer/6010255?p=lsa_blocked&hl=en-GB&visit_id=636759033269131098-410976990&rd=1 dan edinebilirsiniz.
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = 'xyz@gmail.com'  # gmail adresinizi girin
    MAIL_PASSWORD = 'sifre'  # gmail şifrenizi girin
    MAIL_DEFAULT_SENDER = '"MyApp" <xyz@gmail.com>'

    USER_APP_NAME = "Otel Rezervasyon"
    USER_ENABLE_EMAIL = True        
    USER_ENABLE_USERNAME = False    
    USER_EMAIL_SENDER_NAME = USER_APP_NAME
    USER_EMAIL_SENDER_EMAIL = "noreply@example.com"
    USER_LOGIN_TEMPLATE='/login/index.html'

def create_app():
    """ Flask application factory """

    app = Flask(__name__)
    bcrypt = Bcrypt(app)
    app.config.from_object(__name__+'.ConfigClass')
    login_manager=LoginManager(app)
 

    babel = Babel(app)
    @babel.localeselector
    def get_locale():
        translations = [str(translation)
                        for translation in babel.list_translations()]

    db = SQLAlchemy(app)
 
    # Define the User data-model.
    # NB: Make sure to add flask_user UserMixin !!!
    class User(db.Model, UserMixin):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        active = db.Column('is_active', db.Boolean(),
                           nullable=False, server_default='1')

        # User authentication information. The collation='NOCASE' is required
        # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
        email = db.Column(db.String(255, collation='NOCASE'),
                          nullable=False, unique=True)
        email_confirmed_at = db.Column(db.DateTime())
        password = db.Column(db.String(255), nullable=False, server_default='')

        # User information
        first_name = db.Column(
            db.String(100, collation='NOCASE'), nullable=False, server_default='')
        last_name = db.Column(
            db.String(100, collation='NOCASE'), nullable=False, server_default='')

        # Define the relationship to Role via UserRoles
        roles = db.relationship('Role', secondary='user_roles')

    # Define the Role data-model
    class Role(db.Model):
        __tablename__ = 'roles'
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(50), unique=True)

    # Define the UserRoles association table
    class UserRoles(db.Model):
        __tablename__ = 'user_roles'
        id = db.Column(db.Integer(), primary_key=True)
        user_id = db.Column(db.Integer(), db.ForeignKey(
            'users.id', ondelete='CASCADE'))
        role_id = db.Column(db.Integer(), db.ForeignKey(
            'roles.id', ondelete='CASCADE'))

    class Oteller(db.Model):
        __tablename__ = 'oteller'
        otel_id = db.Column(db.Integer(), autoincrement=True, primary_key=True)
        isim=db.Column(db.String(255))
        adres=db.Column(db.String(255))
        yildiz=db.Column(db.Integer())
        image_url=db.Column(db.String(500))

    class Odalar(db.Model):
        __tablename__ = 'odalar'
        oda_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
        fiyat=db.Column(db.Integer())
        kac_kisilik = db.Column(db.Integer())
        otel_id = db.Column(db.Integer, db.ForeignKey('oteller.otel_id', ondelete='CASCADE'))
        active = db.Column('is_active', db.Boolean(),
                           nullable=False, server_default='1')
    class Rezervasyonlar(db.Model):
        __tablename__ = 'rezervasyonlar'
        rez_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
        oda_id = db.Column(db.Integer, db.ForeignKey('odalar.oda_id', ondelete='CASCADE'))
        baslangic=db.Column(db.String(20))
        bitis=db.Column(db.String(20))
        fiyat=db.Column(db.Integer)
        users_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
        def serialize(self):
            return {"rez_id": self.rez_id,
                    "oda_id": self.oda_id,
                    "baslangic": self.baslangic,
                    "bitis": self.bitis,
                    "fiyat" :self.fiyat,
                    "users_id": self.users_id}
        

    # Setup Flask-User and specify the User data-model
    user_manager = UserManager(app, db, User)

    # Create all database tables
    db.create_all()
    engine = create_engine('sqlite:///basic_app.sqlite')
    meta = MetaData(engine,reflect=True)
    t_oteller = meta.tables['oteller']
    t_odalar =  meta.tables['odalar']
    t_rez = meta.tables['rezervasyonlar']

    # Create 'member@example.com' user with no roles
    if not User.query.filter(User.email == 'member@example.com').first():
        user = User(
            email='member@example.com',
            email_confirmed_at=datetime.datetime.utcnow(),
            password=user_manager.hash_password('Password1'),
        )
        db.session.add(user)
        db.session.commit()

    # Create 'admin@example.com' user with 'Admin' and 'Agent' roles
    if not User.query.filter(User.email == 'admin@example.com').first():
        user = User(
            email='admin@example.com',
            email_confirmed_at=datetime.datetime.utcnow(),
            password=user_manager.hash_password('Password1'),
        )
        user.roles.append(Role(name='Admin'))
        user.roles.append(Role(name='Agent'))
        db.session.add(user)
        db.session.commit()
    
    rol=''
    # The Home page is accessible to anyone
    @app.route('/')
    def home_page():
        db_uri = 'sqlite:///basic_app.sqlite'
        engine = create_engine(db_uri)
        conn = engine.connect()
        rows = engine.execute('SELECT * FROM oteller LIMIT 3')
        global rol
        rol=''
        if current_user.is_authenticated:
            rol=engine.execute('SELECT r.name From roles r,user_roles ur,roles rol,users u WHERE u.id='+str(current_user.id)+' AND ur.user_id=u.id AND ur.role_id=rol.id AND rol.name="'+'Admin'+'"').fetchone()
            if rol:
                rol=rol[0]
        return render_template('index.html', oteller=rows,rol=rol)

    @app.route('/anasayfa')
    def anasayfa():
        return redirect('/')


    @app.route('/login')
    def login():
        if current_user.is_authenticated:
            return redirect('/')

        else:
            return render_template('/login/index.html')


    @app.route('/giris_yap', methods=['POST', 'GET'])
    def giris_yap():
        session.pop('sepetim', None)
        sepetim.clear()
        if request.method == 'POST':
            mail = request.form['mail']
            password = request.form['pass']
            con = sql.connect('basic_app.sqlite')
            cur = con.cursor()
            user = User.query.filter_by(email = mail).first()
            msg = 	"Kullanıcı bulunamadı"
            if user:
                if bcrypt.check_password_hash(user.password, password):
                    user.authenticated = True
                    db.session.add(user)
                    db.session.commit()
                    login_user(user, remember=True)
                    return redirect('/')
               
            return render_template('./login/index.html',msg = msg,hata = 'alert alert-danger')


 
    @app.route('/register')
    def register():
        return render_template('/register/index.html')

    @app.route('/kayit', methods=['POST', 'GET'])
    def kayit():
        if request.method == 'POST':
            mail = request.form['mail']
            password = request.form['pass']
            if not User.query.filter(User.email == mail).first():
                user = User(
                    email=mail,
                    email_confirmed_at=datetime.datetime.utcnow(),
                    password=user_manager.hash_password(password),
                )
                role = Role.query.filter_by(name='Uye').one()
                user.roles.append(role)
                db.session.add(user)
                db.session.commit()
                return render_template('/register/index.html',msg = 'Kayıt başarıyla eklendi',hata='alert alert-success')
            else:
                return render_template('/register/index.html',msg='Bu kişi daha önce kaydolmuş',hata ='alert alert-danger')
        

 

    @app.route('/otelekleme')
    @roles_required('Admin')  # Use of @roles_required decorator
    def otelekleme():
        return render_template('otelekleme.html',rol=rol)

    @app.route('/OtelEkle', methods=['POST', 'GET'])
    def OtelEkle():
        otel = Oteller(
            isim=request.form['isim'],
            adres=request.form['adres'],
            yildiz=request.form['yildiz'],
         
        )
        db.session.add(otel)
        msg = "Otel başarıyla eklendi"
        db.session.commit()
        return render_template('otelekleme.html', mesaj=msg, alert_tur="alert alert-success")
  
    @app.route('/otellerigetir')
    def otellerigetir():
        oteller=Oteller.query.all()
        global rol
      
        for otel in oteller:
            con = sql.connect('basic_app.sqlite')
            cur = con.cursor()
            today = strftime("%Y-%m-%d", gmtime())
            print("TODAY :"+today)
            cur.execute("SELECT count(od.oda_id) FROM odalar od JOIN rezervasyonlar r ON r.oda_id=od.oda_id JOIN oteller o ON o.otel_id = od.otel_id WHERE r.baslangic='"+str(today)+"' AND o.otel_id ="+str(otel.otel_id)+"")
            con.commit()
            oran = cur.fetchone()
            cur.execute("SELECT count(oda_id) FROM odalar WHERE otel_id="+str(otel.otel_id)+"")
            con.commit()
            odasayisi = cur.fetchone()
            odasayisi = odasayisi[0]
            sayi = int(oran[0])
            oran2=int((sayi/odasayisi)*100)
            otel.oran=oran2
        return render_template('oteller.html',oteller=oteller,rol=rol)

    @app.route('/otelguncelleme', methods=['POST', 'GET'])
    @roles_required('Admin')  # Use of @roles_required decorator
    def otelguncelleme():
        global rol
        con = sql.connect('basic_app.sqlite')
        otel_id = request.form['otel_id']
        return render_template('otelguncelleme.html',otel_id = otel_id,rol=rol)

    @app.route('/otelguncelle', methods=['POST', 'GET'])
    def otelguncelle():
        otel_id = request.form['otel_id']
        isim = request.form['isim']
        adres = request.form['adres']
        yildiz = request.form['yildiz']
        con = sql.connect('basic_app.sqlite')
        cur = con.cursor()
        cur.execute("UPDATE oteller SET isim=(?),adres=(?),yildiz=(?) WHERE otel_id='"+str(otel_id)+"'",(isim,adres,yildiz))
        con.commit()
        return render_template('otelguncelleme.html',mesaj="Otel başarıyla güncellendi", alert_tur="alert alert-success", oda = oda)

    @app.route('/otelsil', methods=['POST', 'GET'])
    @roles_required('Admin')  # Use of @roles_required decorator
    def otelsil():

        con = sql.connect('basic_app.sqlite')
        otel_id = request.form['otel_id']
        cur = con.cursor()
        cur.execute('DELETE FROM oteller WHERE otel_id ='+str(otel_id)+'')
        cur.execute('DELETE FROM odalar WHERE otel_id='+str(otel_id)+'')
        con.commit()
    
        return redirect('otellerigetir')

    @app.route('/odaekleme')
    @roles_required('Admin')  # Use of @roles_required decorator
    def odaekleme():
        db_uri =  'sqlite:///basic_app.sqlite'
        engine = create_engine(db_uri)
        conn = engine.connect()
        select_st = select([t_oteller.c.isim,t_oteller.c.otel_id])
        otel_isim = conn.execute(select_st)
        return render_template('odaekleme.html',otel_isim = otel_isim)

    @app.route('/OdaEkle', methods=['POST', 'GET'])
    def OdaEkle():
        msg="Hata oluştu"
        oda = Odalar(
            fiyat=request.form['fiyat'],
            otel_id=request.form['otel_id'],
            kac_kisilik=request.form['kac_kisilik']
        )
        db.session.add(oda)
        db.session.commit()
        msg = 'Oda eklendi'
        return redirect('odaekleme')

    oda={}

    @app.route('/odaguncelleme', methods=['POST', 'GET'])
    @roles_required('Admin')  # Use of @roles_required decorator
    def odaguncelleme():
        db_uri =  'sqlite:///basic_app.sqlite'
        engine = create_engine(db_uri)
        conn = engine.connect()
        select_oteller = select([t_oteller.c.isim,t_oteller.c.otel_id])
        otel_isim = conn.execute(select_oteller)
        con = sql.connect('basic_app.sqlite')
        oda_id = request.form['oda_id']
        cur = con.cursor()
        cur.execute('SELECT * FROM odalar WHERE oda_id='+str(oda_id)+'')
        global oda 
        oda = cur.fetchall()
        return render_template('odaguncelleme.html',oda = oda ,otel_isim = otel_isim, oda_id = oda_id)

    @app.route('/odasilme', methods=['POST', 'GET'])
    @roles_required('Admin')  # Use of @roles_required decorator
    def odasilme():

        con = sql.connect('basic_app.sqlite')
        oda_id = request.form['oda_id']
        cur = con.cursor()
        cur.execute('DELETE FROM odalar WHERE oda_id ='+str(oda_id)+'')
        cur.execute('DELETE FROM rezervasyonlar WHERE oda_id ='+str(oda_id)+'')
        con.commit()
        return redirect('otellerigetir')


    @app.route('/OdaGuncelle', methods=['POST', 'GET'])
    def OdaGuncelle():
        msg="Hata oluştu"
        fiyat=request.form['fiyat']
        kac_kisilik=request.form['kac_kisilik']
        oda_id = request.form['oda_id']
        con = sql.connect('basic_app.sqlite')
        cur = con.cursor()
        cur.execute("UPDATE odalar SET fiyat=(?),kac_kisilik=(?) WHERE oda_id='"+str(oda_id)+"'",(fiyat,kac_kisilik))
        con.commit()
        return render_template('odaguncelleme.html',msg="Oda başarıyla güncellendi", hata="alert alert-success", oda = oda)


    @app.route('/odalar', methods=['POST', 'GET'])
    def odalar():
        global rol
        con = sql.connect('basic_app.sqlite')
        secilen_id = request.form['secilen_id']
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT o.isim, od.oda_id, od.kac_kisilik, od.fiyat FROM oteller o INNER JOIN odalar od ON od.otel_id=o.otel_id WHERE o.otel_id ="+secilen_id+" ORDER BY od.oda_id ASC")
        odalar = cur.fetchall()
        return render_template('odalar.html',odalar = odalar,rol=rol)

    @app.route('/rezervasyonlarim')
    @login_required
    def rezervasyonlarim():
        global rol
        con = sql.connect('basic_app.sqlite')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT r.*,ot.isim, o.kac_kisilik FROM odalar o JOIN rezervasyonlar r ON r.oda_id = o.oda_id JOIN oteller ot ON ot.otel_id = o.otel_id WHERE r.users_id="+str(current_user.id)+"")
        rezervasyonlar = cur.fetchall()
        return render_template('rezervasyonlarim.html', rezervasyonlar=rezervasyonlar,rol=rol)
    
    @app.route('/rezsil', methods=['POST', 'GET'])
    @login_required
    def rezsil():
        con = sql.connect('basic_app.sqlite')
        rez_id = request.form['rez_id']
        cur = con.cursor()
        cur.execute('DELETE FROM rezervasyonlar WHERE rez_id ='+str(rez_id)+'')
        con.commit()
        return redirect('rezervasyonlarim')

    sepetim = []
    fiyat=0
    @app.route('/sepetal', methods=['POST', 'GET'])
    @login_required
    def sepetal():
        con = sql.connect('basic_app.sqlite')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM Rezervasyonlar WHERE oda_id ="+request.form['oda_id']+"")
        rezervasyonlar = cur.fetchall()
        baslangicsepet=datetime.datetime.strptime(request.form['baslangic'],'%Y-%m-%d')     
        bitissepet=datetime.datetime.strptime(request.form['bitis'],'%Y-%m-%d')
        baslangic=datetime.datetime.strptime(request.form['baslangic'],'%Y-%m-%d')
        bitis=datetime.datetime.strptime(request.form['bitis'],'%Y-%m-%d')
        global fiyat
        msg=''
        if baslangic<bitis:
            if len(rezervasyonlar)>0:
                for rez in rezervasyonlar:
                    baslangic=datetime.datetime.strptime(rez['baslangic'],'%Y-%m-%d')
                    bitis=datetime.datetime.strptime(rez['bitis'],'%Y-%m-%d') 
                    #baslangicsepet=datetime.datetime.strptime(request.form['baslangic'],'%Y-%m-%d')     
                    #bitissepet=datetime.datetime.strptime(request.form['bitis'],'%Y-%m-%d')
                    if not ((baslangic<=baslangicsepet<=bitis) or (baslangic<=bitissepet<=bitis)):
                        user = current_user.id
                        rez=len(sepetim)+1
                        
                        gunler=bitissepet-baslangicsepet
                        cur.execute('Select * From odalar WHERE oda_id="'+str(request.form['oda_id'])+'"')
                        records = cur.fetchall() 
                        odaucreti=0
                        for row in records:
                            odaucreti=row[1]
                        fiyat=gunler.days*int(odaucreti)

                        rezervasyon = Rezervasyonlar(
                        rez_id=rez,
                        oda_id=request.form['oda_id'],
                        baslangic=request.form['baslangic'],
                        bitis=request.form['bitis'],
                        users_id=user,
                        fiyat=fiyat)
                        if session.get('sepetim'):
                            sepetim.clear()
                            sepetim.extend(session['sepetim'])
                        sepetim.append(rezervasyon.serialize())
                        session.pop('sepetim', None)
                        session['sepetim'] = sepetim   
                    else:
                        return render_template('sepetigoster.html', mesaj="Oda bu tarihler arasında müsait değildir", alert_tur="alert alert-danger")
            else:
                user = current_user.id
                rez=len(sepetim)+1
                gunler=bitissepet-baslangicsepet
                cur.execute('Select * From odalar WHERE oda_id="'+str(request.form['oda_id'])+'"')
                records = cur.fetchall() 
                odaucreti=0
                for row in records:
                    odaucreti=row[1]
                fiyat=gunler.days*int(odaucreti)
                rezervasyon = Rezervasyonlar(
                rez_id=rez,
                oda_id=request.form['oda_id'],
                baslangic=request.form['baslangic'],
                bitis=request.form['bitis'],
                users_id=user,
                fiyat=fiyat)
                if session.get('sepetim'):
                    sepetim.clear()
                    sepetim.extend(session['sepetim'])
                sepetim.append(rezervasyon.serialize())
                session.pop('sepetim', None)
                session['sepetim'] = sepetim 
        return redirect('sepetigetir')

    @app.route('/sepetigetir')
    @login_required
    def sepetigetir():
        if session.get('sepetim'):
            sepetim.clear()
            sepetim.extend(session['sepetim'])
            return render_template('sepetigoster.html', sepet=sepetim)
        else:
            tur = 'alert alert-danger'
            mesaj = 'Sepette ürün yok.'
            return render_template('sepetigoster.html',alert_tur=tur, mesaj=mesaj)

    @app.route('/sepettencikar',methods=['POST', 'GET'])
    def sepettencikar():
        
        id=request.form['rez_id']
        temp=[]   
        for sepet in sepetim:
            if int(sepet['rez_id'])!=int(id): 
                temp.append(sepet)       
        sepetim.clear()
        sepetim.extend(temp)
        session.pop('sepetim', None)
        session['sepetim'] = sepetim
        return redirect('sepetigetir')

    @app.route('/sepetibosalt',methods=['POST', 'GET'])
    def sepetibosalt():
        sepetim.clear()
        session.pop('sepetim', None)
        return redirect('/')

    @app.route('/rezervasyonalpage', methods=['POST', 'GET'])
    def rezervasyonalpage():
        user = current_user.id
        msg=''
        for sepet in sepetim:
            con = sql.connect('basic_app.sqlite')
            con.row_factory = sql.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM Rezervasyonlar WHERE oda_id ="+sepet['oda_id']+"")
            rezervasyonlar = cur.fetchall()
            if len(rezervasyonlar)>0:
                for rez in rezervasyonlar:
                    baslangic=datetime.datetime.strptime(rez['baslangic'],'%Y-%m-%d')
                    bitis=datetime.datetime.strptime(rez['bitis'],'%Y-%m-%d') 
                    baslangicsepet=datetime.datetime.strptime(sepet['baslangic'],'%Y-%m-%d')     
                    bitissepet=datetime.datetime.strptime(sepet['bitis'],'%Y-%m-%d')
                    if not ((baslangic<=baslangicsepet<=bitis) or (baslangic<=bitissepet<=bitis)):
                        rezervasyon = Rezervasyonlar(
                        oda_id=sepet['oda_id'],
                        baslangic=sepet['baslangic'],
                        bitis=sepet['bitis'],
                        users_id=user,
                        fiyat=sepet['fiyat'])
                        db.session.add(rezervasyon)
                        db.session.commit()        
            else:
                rezervasyon = Rezervasyonlar(
                        oda_id=sepet['oda_id'],
                        baslangic=sepet['baslangic'],
                        bitis=sepet['bitis'],
                        fiyat=sepet['fiyat'],
                        users_id=user)
                db.session.add(rezervasyon)
                db.session.commit() 
        return redirect('sepetibosalt')

    return app


# Start development web server
if __name__ == '__main__':
    app = create_app()
   # app.run(host='0.0.0.0', port=5000, debug=True)
    app.run(host='127.0.0.1', port=5000, debug=True)
