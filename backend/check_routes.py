from main import app

print('Registered routes:')
for rule in app.url_map.iter_rules():
    methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f'  [{methods}] {rule.rule}')
