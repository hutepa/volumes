from flask import Flask, render_template, request, flash, redirect, url_for, session, escape


app = Flask(__name__)
import xmltodict
import json
import sys
import ssl
from collections import OrderedDict


if __name__ == '__main__':
    sys.path.append("NetApp")
    from NaServer import *

    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context


class ServerError(Exception):pass



@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('vols'))
    username_session = escape(session['username']).capitalize()
    return render_template('index.html', session_user_name=username_session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('vols'))

    error = None
    try:
        if request.method == 'POST':
            session['username'] = request.form['username']
            session['pass'] = request.form['password']
            session['vserver'] = request.form['vserver']
            if session['vserver'] == "KW1PESANV01":
                IP = '10.200.5.100'
            elif session['vserver'] == "SG1PESANV01":
                IP = '10.201.18.70'

            try:

                s = NaServer(IP, 1, 30)
                s.set_server_type("FILER")
                s.set_transport_type("HTTPS")
                s.set_port(443)
                s.set_style("LOGIN")
                s.set_admin_user(session['username'], session['pass'])
                s.set_vserver(session['vserver'])
                s.set_server_cert_verification("False")
                s.set_hostname_verification("False")

                api = NaElement("volume-get-iter")

                xi = NaElement("desired-attributes")
                api.child_add(xi)

                xi = NaElement("desired-attributes")
                api.child_add(xi)

                xi1 = NaElement("volume-attributes")
                xi.child_add(xi1)
                xi11 = NaElement("volume-id-attributes")
                xi1.child_add(xi11)
                xi11.child_add_string("name", "name")

                xi27 = NaElement("volume-space-attributes")
                xi1.child_add(xi27)
                xi27.child_add_string("size-total", "<size-total>")
                xi27.child_add_string("percentage-size-used", "<percentage-size-used>")
                api.child_add_string("max-records", "1000")
                xo = s.invoke_elem(api)
                if (xo.results_status() == "failed"):
                    print ("Error:\n")
                    print (xo.sprintf())
                    sys.exit(1)
                else:
                   # print (xo.sprintf())
                    vols = xo.child_get("attributes-list").children_get()
                    data = []
                    for vol in vols:
                        mydict = xmltodict.parse(vol.sprintf())
                        if 'volume-space-attributes' not in mydict['volume-attributes']:
                            continue

                        dicty = mydict['volume-attributes']['volume-id-attributes'].copy()
                        dicty.update(mydict['volume-attributes']['volume-space-attributes'])
                        dicty['size-total'] = ('%.0f' % (float(int(dicty['size-total'].strip())) / 1024 / 1024 / 1024))
                        del dicty['owning-vserver-name']
                        dictyy = OrderedDict()
                        dictyy['name'] = dicty['name']
                        dictyy['size-total'] = dicty['size-total'] + ' GB'
                        dictyy['percentage-size-used'] = dicty['percentage-size-used'] + ' %'
                        data.append(dictyy)

            except Exception, err:
                print "Error!"
                print Exception, err


    except ServerError as e:
        error = str(e)

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/vols', methods=['GET', 'POST'])
def listVols():
    with open('volumes.json') as f:
        dataa = json.load(f, object_pairs_hook=OrderedDict)
        alldict = dict()
        for i in range(len(dataa)):
            k = dataa[i]['volume-attributes']
            for key in k['volume-space-attributes'].keys():
                if key == 'size':
                    vol_size = k['volume-space-attributes'][key]
                    print vol_size
                    print "\n"
                    break
            aggr_name = k['volume-id-attributes']['containing-aggregate-name']
            vol_name = k['volume-id-attributes']['name']

            if aggr_name in alldict:
                alldict[aggr_name].append([vol_name, vol_size])
            else:
                alldict[aggr_name] = [[vol_name, vol_size]]
    return render_template('vols.html', templates=tmpa, folders=fldrs, myvols=alldict)



if __name__ == '__main__':
    app.run(host='0.0.0.0')
