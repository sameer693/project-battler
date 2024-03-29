from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session,jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, game_required
from games import st_pa_sc,oddeve
from random import randint
# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_COOKIE_NAME"] = "session"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///database.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash('must provide username')
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('must provide password')
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"],request.form.get("password")):
            flash('invalid username and/or password')
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("layout.html")

@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            flash('must provide username')
            return apology('must provide username')
        elif not request.form.get("password"):
            flash("must provide password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("password doesnt match", 400)
            return apology('password doesnt match')
        #check if username taken
        rows = db.execute("SELECT username FROM users WHERE username = ?",request.form.get("username"))
        print(rows)
        if len(rows)==1:
            flash('username already exist')
            return apology('username already exist')
        #checks all the input now genrate hash
        hash=generate_password_hash(request.form.get("password"),method='pbkdf2:sha256',salt_length=8)

        db.execute('INSERT INTO users (username,hash) values(?,?)',request.form.get("username"),hash)
        flash('You were successfully registered in')
        return redirect("/")
    # User reached route via GET
    else:
        return render_template("layout.html")

#fetch friend request
@app.route("/frequest",methods=["GET", "POST"]) 
@login_required
def frequest():
    if request.method== "POST":
        if not request.form.get("username"):
            flash('must provide username')
            return redirect("/frequest")
        if not request.form.get("action"):
            flash('must provide action')
            return apology("no action",400)
        #accept friend request
        if request.form.get("action")=="1":
            db.execute("UPDATE relation SET status=1 WHERE uid_ac=? AND uid_in=?",session["user_id"],request.form.get("username"))
            flash('friend added')
        #delete friend or request 
        elif request.form.get("action")=="0":
            db.execute("DELETE FROM relation WHERE  uid_ac=? AND uid_in=?",session["user_id"],request.form.get("username"))
            flash('friend delted')
        else:
            flash('must provide action')
            return apology("no action",400)
        return redirect("/frequest")
    else:
        rows=db.execute("SELECT id,username FROM users WHERE id IN (SELECT uid_in FROM relation WHERE uid_ac=? AND status=0)",session["user_id"])
        #list of names of friend request from
        if len(rows)<1:
            flash("no requests")
            return apology("no requests",400)
        return render_template("frequest.html",rows=rows)

#to show available friends on search and not self
@app.route("/searchfriend")
@login_required
def showfriend():
    if not request.args.get("q"):
        rows=[]
    rows = db.execute("SELECT username FROM users WHERE username LIKE ? and NOT id=? LIMIT 10","%"+request.args.get("q")+"%",session["user_id"])
    return jsonify(rows) 

#to addfriend to relation make request not to same existing friend also
@app.route("/addfriend",methods=["GET", "POST"])
@login_required
def addfriend():
    if request.method== "POST":
        if not request.form.get("username"):
            flash('must provide username')
            return redirect("/addfriend")
        #add id not username
        rows=db.execute("SELECT id FROM users WHERE username=?",request.form.get("username"))
        if len(rows) != 1 :
            flash('invalid username')
            return redirect("/addfriend")
        if session["user_id"]==rows[0]["id"]:
            flash("self not allowed")
            return redirect("/addfriend")
        #check if not a pre-existing friend
        check=db.execute("SELECT username FROM users WHERE id in(SELECT uid_in FROM relation WHERE uid_ac=? UNION SELECT uid_ac FROM relation WHERE uid_in=?) ",session["user_id"],session["user_id"])
        for c in check:
            if request.form.get("username") in c["username"]:
                flash("already a friend or friend request has been made go check my friend or request")
                return redirect("/addfriend")

        db.execute("INSERT INTO relation (uid_in,uid_ac)VALUES(?,?);",session["user_id"],rows[0]["id"])
        flash('friend request intiated')
        return redirect("/addfriend")
    else:
        return render_template("friends.html")
@app.route("/myfriend")
@login_required
def myfriend():   
    #get all ids of friend and from that get names
    rows=db.execute("SELECT id,username FROM users WHERE id in(SELECT uid_in FROM relation WHERE uid_ac=? AND status=1 UNION SELECT uid_ac FROM relation WHERE uid_in=? AND status=1) ",session["user_id"],session["user_id"])
    if len(rows)<1:
        flash("no friends go and add some")
        return apology("no friends",400)      
    return render_template("myfriend.html",rows=rows)

#play game
games=[{"id":0,"name":"rockpaper"},{"id":1,"name":"oddeve cricket"}]#list of games

#start a game invite
@app.route("/startgame",methods=["GET", "POST"])
@login_required
def startgame():
    if request.method == "POST":
        if not request.form.get("username"):
            flash('must provide username')
            return redirect("/startgame")
        if not request.form.get("game"):
            flash('must provide game name')
            return redirect("/startgame")
        for c in games:
            if str(c["id"])==request.form.get("game"):
                break
        else:
            flash('must provide valid game')
            return redirect("/startgame")
        rid=db.execute("SELECT rid FROM relation WHERE (uid_in =? AND uid_ac=?) OR (uid_in =? AND uid_ac=?)",session["user_id"],request.form.get("username"),request.form.get("username"),session["user_id"])
        if len(rid)!=1:
            flash("must provide correct info")
            return apology("friend not in the list",400)
        db.execute("INSERT INTO ginvite (player1,player2,rid,game_id) VALUES (?,?,?,?)",session["user_id"],request.form.get("username"),rid[0]["rid"],request.form.get("game"))
        flash("request made succefully to start game")
        return redirect("/")
    else:
        rows=db.execute("SELECT id,username FROM users WHERE id in(SELECT uid_in FROM relation WHERE uid_ac=? AND status=1 UNION SELECT uid_ac FROM relation WHERE uid_in=? AND status=1) ",session["user_id"],session["user_id"])
        if len(rows)<1:
            flash("no friends go and add some")
            return apology("no friends",400)
        return render_template("startgame.html",rows=rows,games=games)             
#handle game invitest player1 is request maker and player2 is accepter
@app.route("/gameinvite",methods=["GET", "POST"])
@login_required
def gameinvite():
    if request.method == "POST":    
        if not request.form.get("action"):
            flash("no action")
            return apology("no action",400)
        if not request.form.get("gid"):
            flash("no selected")
            return apology("no selected",400)
        if not request.form.get("game_id"):
            flash("no selected")
            return apology("no selected game_id",400)
        #accept gamerequest
        if request.form.get("action")=="1":
            db.execute("UPDATE ginvite SET status=1 WHERE gid=?",request.form.get("gid"))
            flash('friend added')
            for c in games:
                if str(c["id"])==request.form.get("game_id"):
                    #accept gamerequest for the game we play
                    if c["id"]==0:
                        db.execute("INSERT INTO stonepaper (gid) VALUES (?)",request.form.get("gid"))  
                        break          
                    elif c["id"]==1:
                        db.execute("INSERT INTO oddeve (gid) VALUES(?)",request.form.get("gid"))
                        break
            else:
                flash("no selected type in bound")
                return apology("no selected game_id found",400)
        #delete game request 
        elif request.form.get("action")=="0":
            db.execute("DELETE FROM ginvite WHERE gid=?",request.form.get("gid"))
            flash('friend delted')
        else:
            flash('must provide action')
            return apology("no action",400)  
        return redirect("/gameinvite")       
    else:
        rows=db.execute("SELECT gid,game_id,username FROM ginvite,users WHERE status=0 AND player2=? AND users.id=ginvite.player1",session["user_id"])
        if len(rows)<1:
            return apology("no invites currently to show",400)
        return render_template("gameinvite.html",rows=rows,games=games)
    
@app.route("/play",methods=["GET", "POST"])
@login_required
def play():
    if request.method == "POST": 
        #process it to respective database 
        if not request.form.get("action"):
            flash("no action")
            return apology("no action",400)
        if not request.form.get("gid"):
            flash("no selected")
            return apology("no selected",400)
        #accept gamerequest to play it
        if request.form.get("action")=="1":
            rows=db.execute("SELECT gid FROM ginvite WHERE status=1 AND (player2=? OR player1=?)",session["user_id"],session["user_id"])
            for c in rows:
                if str(c["gid"])==request.form.get("gid"):
                    session["gid"]=c["gid"]
                    return redirect("/game")
            else:
                return apology("unexpected cant open",400) 
        else:
            return apology("unexpected cant open",400)        
    else:
        #continue game list score1,score2 for both
        rows=db.execute("SELECT gid,player1,player2,game_id,a.username AS p1,b.username AS p2,score1,score2 FROM ginvite,users a,users b WHERE status=1 AND (player2=? OR player1=?) AND b.id=ginvite.player2 AND a.id=ginvite.player1",session["user_id"],session["user_id"])
        if len(rows)<1:
            return apology("no games currently to show",400)
        return render_template("continuegame.html",rows=rows,games=games,id=session["user_id"])

#finally play game using module
@app.route("/game",methods=["GET", "POST"])
@login_required
@game_required
def game():
    if request.method == "POST":
        ctr=db.execute("SELECT game_id FROM ginvite WHERE gid=?",session["gid"])
        for c in games:
            if ctr[0]["game_id"] == c["id"]:
                if c["id"]==0:
                    if not request.form.get("choice"):
                        flash("select something")
                        return apology("no choice",400)
                    #to upadte and identify player
                    player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                    if len(player)!=1:
                        return apology("process err",400)
                    if player[0]["player"]==1:
                        check=db.execute("SELECT input_1 AS input FROM stonepaper WHERE gid=?",session["gid"])
                        if check[0]["input"]!=0:
                            flash("already selected your choice")
                            return redirect("/game")
                        db.execute("UPDATE stonepaper SET input_1=? WHERE gid=?", request.form.get("choice"),session["gid"])
                    else:
                        check=db.execute("SELECT input_2 AS input FROM stonepaper WHERE gid=?",session["gid"])
                        if check[0]["input"]!=0:
                            flash("already selected your choice")
                            return redirect("/game")
                        db.execute("UPDATE stonepaper SET input_2=? WHERE gid=?", request.form.get("choice"),session["gid"])
                    flash("selected your choice")
                    return redirect("/game")
                #to do
                elif c["id"]==1:
                    if not request.form.get("choice"):
                        flash("select something")
                        return apology("no choice",400)
                    #to upadte and identify player
                    player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                    if len(player)!=1:
                        return apology("process err",400)
                    if player[0]["player"]==1:
                        check=db.execute("SELECT input_1 AS input FROM oddeve WHERE gid=?",session["gid"])
                        if check[0]["input"]!=0:
                            flash("already selected your choice")
                            return redirect("/game")
                        db.execute("UPDATE oddeve SET input_1=? WHERE gid=?", request.form.get("choice"),session["gid"])
                    else:
                        check=db.execute("SELECT input_2 AS input FROM oddeve WHERE gid=?",session["gid"])
                        if check[0]["input"]!=0:
                            flash("already selected your choice")
                            return redirect("/game")
                        db.execute("UPDATE oddeve SET input_2=? WHERE gid=?", request.form.get("choice"),session["gid"])
                    flash("selected your choice")
                    return redirect("/game")
        else:
            return apology("out of bound leave session or make a new game",400)
    else:
        ctr=db.execute("SELECT game_id FROM ginvite WHERE gid=?",session["gid"])
        for c in games:
            if ctr[0]["game_id"] == c["id"]:
                if c["id"]==0:
                    return render_template("stonepaper.html")
                elif c["id"]==1:
                    return render_template("oddeve.html")
        else:           
            return apology("out of bound leave session or make a new game",400)
 
@app.route("/response")
@login_required
@game_required
def response():
    #to update and identify player 
    #also to keep a previous record of game till both have not seen it after tha clear the previous parody
    ctr=db.execute("SELECT game_id FROM ginvite WHERE gid=?",session["gid"])
    for c in games:
        if ctr[0]["game_id"] == c["id"]:
            #stone paper
            if c["id"]==0:
                player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                if len(player)!=1:
                    return apology("process err",400)
                if player[0]["player"]==1:
                    #you are player 1
                    seen=db.execute("SELECT seen FROM stonepaper WHERE gid=?",session["gid"])
                    #no results have been shown
                    if seen[0]["seen"]==0:
                        check=db.execute("SELECT input_1,input_2 FROM stonepaper WHERE gid=?",session["gid"])
                        msg,code=st_pa_sc(check)
                        #if same reset inputs and tell same input came
                        if code==9:
                            db.execute("UPDATE stonepaper SET input_1=0,input_1=0 WHERE gid=?",session["gid"])
                            #create a parody data for other user
                            db.execute("UPDATE stonepaper SET input_1=0,input_2=0,parody1=?,parody2=?,seen=1 WHERE gid=?",check[0]["input_1"],check[0]["input_2"],session["gid"])
                        elif code==1:        
                            db.execute("UPDATE ginvite SET score1=score1+1 WHERE gid=?",session["gid"])
                            #create a parody data for other user
                            db.execute("UPDATE stonepaper SET input_1=0,input_2=0,parody1=?,parody2=?,seen=1 WHERE gid=?",check[0]["input_1"],check[0]["input_2"],session["gid"])
                        elif code==2:
                            db.execute("UPDATE ginvite SET score2=score2+1 WHERE gid=?",session["gid"])
                            #create a parody data for other user and seen as 1
                            db.execute("UPDATE stonepaper SET input_1=0,input_2=0,parody1=?,parody2=?,seen=1 WHERE gid=?",check[0]["input_1"],check[0]["input_2"],session["gid"])
                        return jsonify(code=code,msg=msg,input=check[0]["input_2"])
                    # result already shown to 2nd player
                    elif seen[0]["seen"]==2:
                        check=db.execute("SELECT parody1 AS input_1,parody2 AS input_2 FROM stonepaper WHERE gid=?",session["gid"])
                        msg,code=st_pa_sc(check)
                        #now both have result return to default
                        db.execute("UPDATE stonepaper SET seen=0 WHERE gid=?",session["gid"])
                        return jsonify(code=code,msg=msg,input=check[0]["input_2"])
                else:
                    #you are player 2
                    seen=db.execute("SELECT seen FROM stonepaper WHERE gid=?",session["gid"])
                    #no results have been shown
                    if seen[0]["seen"]==0:
                        check=db.execute("SELECT input_1,input_2 FROM stonepaper WHERE gid=?",session["gid"])
                        msg,code=st_pa_sc(check)
                        #if same reset inputs and tell same input came
                        if code==9:
                            db.execute("UPDATE stonepaper SET input_1=0,input_1=0 WHERE gid=?",session["gid"])
                            #create a parody data for other user
                            db.execute("UPDATE stonepaper SET input_1=0,input_2=0,parody1=?,parody2=?,seen=2 WHERE gid=?",check[0]["input_1"],check[0]["input_2"],session["gid"])
                        elif code==1:        
                            db.execute("UPDATE ginvite SET score1=score1+1 WHERE gid=?",session["gid"])
                            #create a parody data for other user
                            db.execute("UPDATE stonepaper SET input_1=0,input_2=0,parody1=?,parody2=?,seen=2 WHERE gid=?",check[0]["input_1"],check[0]["input_2"],session["gid"])
                        elif code==2:
                            db.execute("UPDATE ginvite SET score2=score2+1 WHERE gid=?",session["gid"])
                            #create a parody data for other user
                            db.execute("UPDATE stonepaper SET input_1=0,input_2=0,parody1=?,parody2=?,seen=2 WHERE gid=?",check[0]["input_1"],check[0]["input_2"],session["gid"])
                        return jsonify(code=code,msg=msg,input=check[0]["input_1"])
                    # result already shown to 1st player
                    elif seen[0]["seen"]==1:
                        check=db.execute("SELECT parody1 AS input_1,parody2 AS input_2 FROM stonepaper WHERE gid=?",session["gid"])
                        msg,code=st_pa_sc(check)
                        #now both have result return to default
                        db.execute("UPDATE stonepaper SET seen=0 WHERE gid=?",session["gid"])
                        return jsonify(code=code,msg=msg,input=check[0]["input_1"])
            #oddeve game cricket
            elif c["id"]==1:
                seen=db.execute("SELECT seen FROM oddeve WHERE gid=?",session["gid"])
                #you are player 1
                check=db.execute("SELECT input_1,input_2,innings,run1,run2,wicket1,wicket2 FROM oddeve WHERE gid=?",session["gid"])
                #no results have been shown
                if seen[0]["seen"]==0:
                    #run to be added maybe
                    if check[0]["innings"]==0:
                        #toss
                        inn=randint(1,2)
                        player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                        if len(player)!=1:
                            return apology("process err",400)
                        if player[0]["player"]==1:
                            db.execute("UPDATE oddeve SET innings=?,seen=1,msg=?,code=-1 WHERE gid=?",inn,f"toss won by player{inn} and he will bat",session["gid"])               
                        else:
                            db.execute("UPDATE oddeve SET innings=?,seen=2,msg=?,code=-1 WHERE gid=?",inn,f"toss won by player{inn} and he will bat",session["gid"])                                
                        return jsonify(code=-1,msg=f"toss won by player{inn} and he will bat")
                    #now do it
                    msg,code=oddeve(check)
                    if check[0]["innings"]==1:
                        if code!=0:
                            if code==1:
                                db.execute("UPDATE ginvite SET score1=score1+1 WHERE gid=?",session["gid"])
                                db.execute("UPDATE oddeve SET innings=0,wicket1=3,wicket2=3,run1=0,run2=0 WHERE gid=?",session["gid"])
                            elif code==2:
                                db.execute("UPDATE ginvite SET score2=score2+1 WHERE gid=?",session["gid"])
                                db.execute("UPDATE oddeve SET innings=0,wicket1=3,wicket2=3,run1=0,run2=0 WHERE gid=?",session["gid"])
                        
                            elif code==3:
                                db.execute("UPDATE oddeve SET wicket1=wicket1-1 WHERE gid=?",session["gid"])
                            elif code==4:
                                db.execute("UPDATE oddeve SET run1=run1+? WHERE gid=?",check[0]["input_1"],session["gid"])
                            elif code==5:
                                db.execute("UPDATE oddeve SET innings=2 WHERE gid=?",session["gid"])
                                check[0]["innings"]=2
                            #keeping record of what happend and who saw
                            player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                            if len(player)!=1:
                                return apology("process err",400)
                            if player[0]["player"]==1:
                                db.execute("UPDATE oddeve SET code=?,msg=?,seen=1,input_1=0,input_2=0,opinput=? WHERE gid=?",code,msg,check[0]["input_2"],session["gid"])       
                                return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],opinput=check[0]["input_2"],inning=check[0]["innings"])
                            else:
                                db.execute("UPDATE oddeve SET code=?,msg=?,seen=2,input_1=0,input_2=0,opinput=? WHERE gid=?",code,msg,check[0]["input_1"],session["gid"])   
                                return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],opinput=check[0]["input_1"],inning=check[0]["innings"])
                        else:
                            return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],inning=check[0]["innings"])
                    else:
                        if code!=0:
                            if code==1:
                                db.execute("UPDATE ginvite SET score1=score1+1 WHERE gid=?",session["gid"])
                                db.execute("UPDATE oddeve SET innings=0,wicket1=3,wicket2=3,run1=0,run2=0 WHERE gid=?",session["gid"])
                            
                            elif code==2:
                                db.execute("UPDATE ginvite SET score2=score2+1 WHERE gid=?",session["gid"])
                                db.execute("UPDATE oddeve SET innings=0,wicket1=3,wicket2=3,run1=0,run2=0 WHERE gid=?",session["gid"])
                            
                            elif code==3:
                                db.execute("UPDATE oddeve SET wicket2=wicket2-1 WHERE gid=?",session["gid"])
                            elif code==4:
                                db.execute("UPDATE oddeve SET run2=run2+? WHERE gid=?",check[0]["input_2"],session["gid"])
                            elif code==5:
                                db.execute("UPDATE oddeve SET innings=1 WHERE gid=?",session["gid"])
                                check[0]["innings"]=1
                            #keeping record of what happend and who saw
                            player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                            if len(player)!=1:
                                return apology("process err",400)
                            if player[0]["player"]==1:
                                db.execute("UPDATE oddeve SET code=?,msg=?,seen=1,input_1=0,input_2=0,opinput=? WHERE gid=?",code,msg,check[0]["input_2"],session["gid"])
                                return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],opinput=check[0]["input_2"],inning=check[0]["innings"])
                              
                            else:
                                db.execute("UPDATE oddeve SET code=?,msg=?,seen=2,input_1=0,input_2=0,opinput=? WHERE gid=?",code,msg,check[0]["input_1"],session["gid"]) 
                                return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],opinput=check[0]["input_1"],inning=check[0]["innings"])
                            
                        else:
                            return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],inning=check[0]["innings"])
                elif seen[0]["seen"]==1:
                    player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                    if len(player)!=1:
                        return apology("process err",400)
                    if player[0]["player"]==2:
                        prev=db.execute("SELECT code,msg,opinput FROM oddeve WHERE gid=?",session["gid"])
                        db.execute("UPDATE oddeve SET seen=0 WHERE gid=?",session["gid"])   
                        return jsonify(code=prev[0]["code"],msg=prev[0]["msg"],run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],opinput=prev[0]["opinput"],inning=check[0]["innings"])
                    #he already saw it 
                    else:
                        msg,code=oddeve(check)
                        return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],inning=check[0]["innings"])

                elif seen[0]["seen"]==2:
                    player=db.execute("SELECT CASE WHEN player1=? THEN 1 WHEN player2=? THEN 2 END as player FROM ginvite WHERE gid=?",session["user_id"],session["user_id"],session["gid"])
                    if len(player)!=1:
                        return apology("process err",400)
                    if player[0]["player"]==1:
                        prev=db.execute("SELECT code,msg,opinput FROM oddeve WHERE gid=?",session["gid"])
                        db.execute("UPDATE oddeve SET seen=0 WHERE gid=?",session["gid"]) 
                        return jsonify(code=prev[0]["code"],msg=prev[0]["msg"],run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],opinput=prev[0]["opinput"],inning=check[0]["innings"])               
                    #he already saw it 
                    else:
                        msg,code=oddeve(check)
                        return jsonify(code=code,msg=msg,run2=check[0]["run2"],run1=check[0]["run1"],wicket1=check[0]["wicket1"],wicket2=check[0]["wicket2"],inning=check[0]["innings"])

    else:           
        return apology("out of bound leave session or make a new game",400)  