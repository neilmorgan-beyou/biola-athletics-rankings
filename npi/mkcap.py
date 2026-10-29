"""Build an npi/captures/<sport>-<date>.json from a saved NCAA.com NPI rankings page.

    python3 npi/mkcap.py page.html "Women's Soccer" soccer-women 2026-10-28 npi/captures/wsoc-2026-10-28.json

Args: saved page HTML, sport name, ncaa.com code, release date, output file. Then `npi.py add`.
Used for the 2026-10-28 catch-up (see ROUTINE.md)."""
import re,html,json,sys
from datetime import datetime
src,sport,code,rel,out=sys.argv[1:6]
s=open(src).read()
t=re.search(r'<table.*?</table>',s,re.S).group(0)
rows=[[html.unescape(re.sub(r'<[^>]+>','',c)).strip() for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>',r,re.S)] for r in re.findall(r'<tr.*?</tr>',t,re.S)]
hdr,body=rows[0],[r for r in rows[1:] if r]
thru=datetime.strptime(re.search(r'Through Games ([A-Z]{3})\. (\d+), (\d{4})',s).expand(r'\1 \2 \3').title(),'%b %d %Y').date().isoformat()
pub=re.search(r'datePublished":"([^"]+)',s).group(1)
b=[r for r in body if r[0]=='Biola'][0]
reg=b[2]
regrows=sorted([(int(r[3]),r[0]) for r in body if r[2]==reg])
names={'TEAM':'Team','CONFERENCE':'Conference','REGION':'Region','NPI RANK':'NPI Rank','NPI':'NPI','PREVNPI':'Prev NPI','DIIWL':'DII WL','ADJW/L':'Adj W/L','ADJWIN%':'AdjWin%','WINVALUE':'Win Value','LOSSVALUE':'Loss Value','QWB':'QWB','VABOVE':'vAbove','VBELOW':'vBelow'}
cap={"sport":sport,"season":"2026","official":True,"release_date":rel,"through":thru,
 "ncaa_com_url":f"https://www.ncaa.com/rankings/{code}/d2/npi-rankings","ncaa_com_published":pub,
 "source_url":f"https://stats.ncaa.org/selection_rankings/nitty_gritties/2027/{'MSO' if 'men' in code and 'women' not in code else 'WSO'}/2/current_rankings",
 "teams_nationally":len(body),"national_rank":int(b[3]),"npi":b[4],"record":b[6],
 "region":reg.title().replace('Super-Region','Super-Region') if 'SUPER' in reg else reg.title(),
 "region_rank":[n for _,n in regrows].index('Biola')+1,"region_teams":len(regrows),
 "region_standings":[list(x) for x in regrows],
 "biola_row":[[names.get(h,h),v] for h,v in zip(hdr,b)],
 "read":f"Read {datetime.now().date()} by Claude from the table on NCAA.com's own NPI page (Through Games {thru}; {len(body)} teams; published {pub}), by plain page fetch; stats.ncaa.org was not opened. Region rank = Biola's position among {reg} teams sorted by NPI rank."}
json.dump(cap,open(out,'w'),indent=1)
print({k:v for k,v in cap.items() if k not in('region_standings','biola_row')})
