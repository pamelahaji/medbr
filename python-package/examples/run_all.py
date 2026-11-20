# Run after preparing the data (see README).
import webbrowser
from medbr import facilities, mortality, birth, plancoverage, beds, beneficiaries


facilities(city=355030).save('facilities.html')
webbrowser.open('facilities.html')

# optional filter: ufs=['SP', 'RJ']
beds().save('beds.html')
webbrowser.open('beds.html')

# optional filter: ufs=['SP', 'RJ']
beneficiaries().save('beneficiaries.html')
webbrowser.open('beneficiaries.html')

birth(start_at='2021-01-01', end_at='2022-01-01').save('birth.html')
webbrowser.open('birth.html')

# filters start_at and end_at
mortality(start_at='2021-01-01', end_at='2022-01-01').save('mortality.html')
webbrowser.open('mortality.html')

# optional filters: ufs and operators
plancoverage(ufs=['SP', 'RJ']).save('plancoverage.html')
webbrowser.open('plancoverage.html')
