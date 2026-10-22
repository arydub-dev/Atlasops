"""Independent read-only SQL oracle: deliberately does not import product services."""
import json
import sqlite3
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
if not (root / 'SYNTHETIC_ONLY').is_file():
    raise SystemExit('Not a QA run')
fixture = json.loads((root / 'private.json').read_text())
org = fixture['org_id'].replace('-', '')
with sqlite3.connect(f'file:{root}/qa.sqlite?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    rows = [dict(r) for r in db.execute('SELECT i.*, p.sku FROM inventory i JOIN products p ON p.id=i.product_id WHERE i.organization_id=? AND i.is_current=1', (org,))]
    hp = next(r for r in rows if r['sku'] == 'HP-240')
    low = sum(r['quantity'] <= r['reorder_point'] for r in rows)
    over = sum(r['quantity'] > r['reorder_point'] and r['max_stock'] > 0 and r['quantity'] >= r['max_stock'] for r in rows)
    dup = db.execute('SELECT COUNT(*) FROM (SELECT warehouse_id,product_id FROM inventory WHERE organization_id=? AND is_current=1 GROUP BY warehouse_id,product_id HAVING COUNT(*)>1)', (org,)).fetchone()[0]
    output = {'positions': len(rows), 'total_units': sum(r['quantity'] for r in rows), 'low_stock': low, 'overstock': over,
        'duplicate_positions': dup, 'hp_quantity': hp['quantity'], 'hp_replenishment': max((hp['max_stock'] or 2*hp['reorder_point'])-hp['quantity'],0) if hp['quantity'] <= hp['reorder_point'] else 0,
        'warehouse_total': db.execute('SELECT SUM(current_inventory) FROM warehouses WHERE organization_id=?',(org,)).fetchone()[0]}
print(json.dumps(output))
