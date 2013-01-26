from MySQLdb import connect
from subprocess import call 
from string import replace
import pickle

def get_db():
    return connect(user="aixada", passwd="aixada", db="aixada")

def shop_dates(db):
#    return ['2005-01-12', '2005-01-19']
    c = db.cursor()
    c.execute("""
select 
  distinct date_for_order 
from 
  aixada_order_item 
where
  date_for_order >= '1950-01-01'
order by
  date_for_order;
""")
    return c.fetchall()
    

def ufs_at_date(db, date):
    c = db.cursor()
    c.execute("""
select 
  distinct uf_id
from
  aixada_order_item
where 
  date_for_order = %s
order by uf_id""",
              (date,))
    return c.fetchall()
    
def total_spent(db, uf_id, date):
    c = db.cursor()
    c.execute("""
select 
  -sum(quantity) 
from 
  aixada_account 
where 
  account_id=%s 
  and 
  ts between %s and %s + interval 1 day
  and
  quantity < 0;
""", (1000 + uf_id, date, date))
    return c.fetchall()[0][0]

def products_bought(db, uf_id, date):
    c = db.cursor()
    c.execute("""
select 
  quantity, product_id
from 
  aixada_order_item
where 
  date_for_order = %s and uf_id = %s
group by product_id""",
              (date, uf_id,))
    return c.fetchall()

def xname(date, product):
    return 'x' + str(product) + '_' + date

def ptolname(date, uf):
    return 'p' + str(uf) + '_' + date

def ntolname(date, uf):
    return 'n' + str(uf) + '_' + date

def make_eqs(date, uf, products, spent, eqs):
    if spent is not None:
        eqstr = 'uf' + str(uf) + '_' + date + ': ' + \
            ' + '.join([str(p[0]) + ' ' + xname(date, p[1]) for p in products]) + \
            ' + ' + ptolname(date, uf) + \
            ' - ' + ntolname(date, uf) + \
            ' = ' + str(spent)
        eqs.append(eqstr)

def lp(date, eqs, ufs, product_vars, special_product_var, maximize=1):
    if maximize==1:
        sign = ' - '
    else:
        sign = ' + '
    return 'minimize ' + \
        ' + '.join(['1000 ' + ptolname(date, uf) + ' + 1000 ' + ntolname(date, uf) for uf in ufs]) + \
        sign + str(special_product_var) + '\nsubject to\n' + \
        '\n'.join(eqs) + \
        '\nbounds\n' + \
        ' >= 0\n'.join(product_vars) + \
        ' >= 0\n' + \
        '\n'.join([ptolname(date, uf) + ' >= 0' for uf in ufs]) + \
        '\n' + \
        '\n'.join([ntolname(date, uf) + ' >= 0' for uf in ufs])

def bound(date, eqs, ufs, product_vars, v, maximize):
    fout = open('prob.lp', 'w')
    fout.write(lp(date, eqs, ufs, product_vars, v, maximize))
    fout.close()
    call(['gurobi_cl', 'OutputFlag=0', 'ResultFile=prob.sol', 'prob.lp'])
    return solution(v)

def solution(special_product_var):
    fin = open('prob.sol', 'r')
    first = True
    for line in fin:
        if first:
            first = False
            try:
                obj = line.split('=')[1]
            except IndexError:
                return None
            continue
        linearray = line.split(' ')
        if linearray[0] == special_product_var:
            return round(float(linearray[1]),2)

def make_bounds(date, bounds):
    eqs = []
    vars = []
    vdate = replace(date, '-', '_')
    ufs = [_uf[0] for _uf in ufs_at_date(db, date)]
    for uf in ufs:
        pb = products_bought(db, uf, date)
        for p in pb:
            vars.append(xname(vdate, p[1]))
        ts = total_spent(db, uf, date)
        make_eqs(vdate, uf, pb, ts, eqs)
    product_vars = set(vars)
    for v in product_vars:
        min_res = bound(vdate, eqs, ufs, product_vars, v, 0)
        max_res = bound(vdate, eqs, ufs, product_vars, v, 1)
        bounds[v] = [min_res, max_res]
    return bounds

def save_bounds(db, bounds):
    entries = []
    for var, bd in bounds.iteritems():
        [xproduct, y, m, d] = var.split('_')
        entries.append([xproduct[1:], y + '-' + m + '-' + d, bd[0], bd[1]])

    print entries
    c = db.cursor()
    c.executemany("""
replace into
  aixada_estimated_prices (product_id, ts, min_estimated_price, max_estimated_price)
values (%s, %s, %s, %s)
""", (entries))


if __name__ == "__main__":
    db = get_db()
    bounds = dict()
    dates = [date[0].strftime("%Y-%m-%d") for date in shop_dates(db)]
    
    for date in dates:
        print date
        bounds = make_bounds(date, bounds)
        save_bounds(db, bounds)
        db.commit()
