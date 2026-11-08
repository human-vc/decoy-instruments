import re
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import scenarios_v2 as V

VERSIONS = ["silent", "implied", "chain"]

FIELDS = {
    "var": str, "alt_var": str, "design": str, "alt_scope": str, "study": str, "named": str, "cite": str,
    "channel_cite": str, "base": str, "implied": str, "consequence": str, "link1": str, "link2": str, "bridge": str,
    "memo": str, "others": list, "alt": str, "unit": str, "topics": list, "treat": str, "outcome": str,
    "plant_re": str, "famous": bool, "source": str,
}

N = {}

N["rain_vote"] = dict(
    var="eday_rain", alt_var="reminder_draw", design="weather", alt_scope="full", source="mellon",
    study="A researcher studies whether higher voter turnout changes presidential election results, using about 3,100 "
          "U.S. counties in the 14 presidential elections from 1948 to 2000. Treatment: county turnout, in percentage "
          "points of the voting-age population. Outcome: the county vote share of the incumbent president's party, in "
          "percentage points.",
    named="A researcher studies whether higher voter turnout changes presidential election results, using county returns "
          "and election-day rainfall for 1948-2000 as in Hansford and Gomez (APSR 2010). Treatment: county turnout. "
          "Outcome: the county vote share of the incumbent president's party.",
    cite="Hansford and Gomez (2010), APSR 104(2): 268-288, doi:10.1017/S0003055410000109",
    channel_cite="Meier, Schmid and Stutzer (2019), European Economic Review 119: 434-451, "
                 "doi:10.1016/j.euroecorev.2019.07.014; Bassi (2019), Journal of Experimental Political Science 6(1): "
                 "17-32, doi:10.1017/XPS.2018.13",
    base="eday_rain: rainfall in inches on election day at the weather station nearest the county centroid, as a "
         "deviation from the county's average election-day rainfall over 1948-2000. Analyses include county and "
         "election-year fixed effects. Each additional inch of rain lowers county turnout by 1.1 percentage points on "
         "average.",
    implied="Post-election surveys by the state election offices found that, among people who voted, those who voted on "
            "a rainy election day reported less willingness to take risks and chose the incumbent party's candidate more "
            "often than voters with the same voting history who voted on a dry day.",
    consequence="Rain can change the incumbent party's vote share whatever the level of turnout.",
    link1="Election days with more than 0.1 inch of rain at the county's station are coded as wet polling days in the "
          "state election offices' polling-day log.",
    link2="Post-election surveys by the state election offices found that, among people who voted, those who voted on a "
          "day coded as a wet polling day in the polling-day log reported less willingness to take risks and chose the "
          "incumbent party's candidate more often than voters with the same voting history who voted on other days.",
    bridge="polling-day log",
    memo="Program memo (state election offices, 2002): County returns are certified by each state's election office. "
         "Voting-age population comes from census interpolations. Polling hours and absentee rules changed in several "
         "states over the period.",
    others=["dem_prev: Democratic vote share in the county in the previous presidential election.",
            "pop_density: county residents per square mile.",
            "pct_rural: share of the county population living in rural areas.",
            "median_inc: county median household income.",
            "south: 1 if the county is in a former Confederate state.",
            "state: state code."],
    alt="reminder_draw: 1 if the county was drawn in that election year's random draw for a nonpartisan mailed reminder "
        "of the election date and polling hours, sent to every registered voter in the county, 0 otherwise; drawn "
        "counties have turnout 2.4 percentage points higher on average. The reminder named no candidate or party, and "
        "the draw changed nothing else in drawn counties.",
    unit="county", topics=["population", "election", "income", "employment", "religion", "housing", "education", "age"],
    treat="county turnout", outcome="incumbent party vote share",
    plant_re=r"risk[- ]?(?:aver|toler|tak|seek|prefer)|willingness to take risks|\bmoods?\b|emotion",
)

N["rain_riot"] = dict(
    var="monsoon_dev", alt_var="works_draw", design="weather", alt_scope="full", source="mellon",
    study="A researcher studies whether faster rural income growth reduces Hindu-Muslim riots, using 290 districts in 15 "
          "Indian states, 1982-1995. Treatment: annual growth of district rural income per person, in percent. Outcome: "
          "number of Hindu-Muslim riots in the district-year.",
    named="A researcher studies whether faster income growth reduces Hindu-Muslim riots in 15 Indian states, 1982-1995, "
          "using rainfall change as in Bohlken and Sergenti (Journal of Peace Research 2010). Treatment: annual income "
          "growth. Outcome: number of Hindu-Muslim riots.",
    cite="Bohlken and Sergenti (2010), Journal of Peace Research 47(5): 535-546, doi:10.1177/0022343310373032",
    channel_cite="Sarsons (2015), Journal of Development Economics 115: 62-72, doi:10.1016/j.jdeveco.2014.12.007",
    base="monsoon_dev: percent deviation of the district's June-September monsoon rainfall from its 1951-1980 average. "
         "Analyses include district and year fixed effects. A 10-point increase in monsoon_dev raises rural income growth "
         "by 1.6 percentage points on average.",
    implied="Police riot registers show that districts downstream of irrigation dams, where canal water keeps crop income "
            "unchanged from one monsoon to the next, record more riots in years of below-average monsoon rainfall, by "
            "about as much as other districts.",
    consequence="Rainfall can change riot counts whatever the growth of rural income.",
    link1="Years in which monsoon_dev is below -10 percent are listed as deficit monsoon years in the state relief manuals.",
    link2="Police riot registers show that districts downstream of irrigation dams, where canal water keeps crop income "
          "unchanged from one monsoon to the next, record more riots in the deficit monsoon years listed in the state "
          "relief manuals, by about as much as other districts.",
    bridge="state relief manuals",
    memo="Program memo (state statistical bureaus, 1997): District income series are compiled from crop output, wages and "
         "prices reported by the state statistical bureaus. Riot counts are coded from newspaper reports and police "
         "records. District boundaries are held fixed at their 1981 definitions.",
    others=["pop_1981: district population in the 1981 census.",
            "muslim_share: Muslim share of the district population in 1981.",
            "urban_share: urban share of the district population in 1981.",
            "literacy: district literacy rate in 1981.",
            "riots_prev: Hindu-Muslim riots in the district in 1975-1981.",
            "state: state code."],
    alt="works_draw: 1 if the district was drawn in the 1985 random draw by which the central government chose 145 of the "
        "290 districts for a rural public-works program paying wages for road and pond construction, 0 otherwise; drawn "
        "districts have rural income growth 1.2 percentage points higher on average. The program changed nothing else "
        "in drawn districts.",
    unit="district", topics=["crop", "price", "wage", "population", "police", "election", "school", "health"],
    treat="rural income growth", outcome="Hindu-Muslim riots",
    plant_re=r"\bdams?\b|\bcanals?\b|downstream",
)

N["rain_health"] = dict(
    var="season_rain", alt_var="transfer_draw", design="weather", alt_scope="full", source="mellon",
    study="A researcher studies whether higher household income improves health, using about 4,000 people in 51 villages "
          "of one region of Tanzania, interviewed up to four times between 1991 and 1994. Treatment: log household income "
          "per adult equivalent. Outcome: number of illness episodes the person reported for the four weeks before the "
          "interview.",
    named="A researcher studies whether higher household income improves health, using the Kagera Health and Development "
          "Survey (Tanzania, 1991-1994) and station rainfall as in Fichera and Savage (World Development 2015). "
          "Treatment: log household income. Outcome: number of illness episodes in the past four weeks.",
    cite="Fichera and Savage (2015), World Development 66: 500-515, doi:10.1016/j.worlddev.2014.09.016",
    channel_cite="Jones, Wort, Morse, Hastings and Gagnon (2007), Malaria Journal 6: 162, doi:10.1186/1475-2875-6-162",
    base="season_rain: rainfall in millimeters at the rainfall station nearest the village during the October-March "
         "rainy season before the interview, as a deviation from the station's long-run average. Analyses include "
         "individual and survey-round fixed effects. Each additional 100 millimeters of rain raises log household "
         "income by 0.08 on average.",
    implied="The regional health office's surveillance records show that malaria cases in the region rise in the months "
            "after rainy seasons with above-average rainfall.",
    consequence="Malaria can raise illness episodes whatever the household's income.",
    link1="Rainy seasons in which season_rain exceeds 100 millimeters are listed as wet seasons in the regional seasonal "
          "calendar.",
    link2="The regional health office's surveillance records show that malaria cases in the region rise in the months "
          "after every wet season listed in the regional seasonal calendar.",
    bridge="regional seasonal calendar",
    memo="Program memo (regional statistical office, 1995): The survey followed households in 51 villages chosen to "
         "represent the region's agroclimatic zones. Interviews were held in four rounds about six to seven months "
         "apart. Income combines crop sales, wages, business profits and the value of home-produced food.",
    others=["age: age in years at the interview.",
            "female: 1 if female.",
            "educ_years: years of completed schooling.",
            "hh_size: number of household members.",
            "dist_clinic: kilometers from the village to the nearest health facility.",
            "land_acres: acres of land the household farms."],
    alt="transfer_draw: 1 if the household's village was drawn in the 1992 random draw by which a regional development "
        "fund chose 25 of the 51 villages for an unconditional cash transfer paid to every household each quarter, 0 "
        "otherwise; households in drawn villages have log income 0.12 higher on average after the draw. The fund "
        "changed nothing else in drawn villages.",
    unit="respondent", topics=["crop", "livestock", "consumption", "schooling", "clinic", "labor", "assets", "household"],
    treat="log household income", outcome="illness episodes",
    plant_re=r"malaria|mosquito",
)

N["waterways"] = dict(
    var="waterways", alt_var="audit_grant", design="geography", alt_scope="full", source="lal",
    study="A researcher studies whether racial residential segregation lowers local public spending, using about 2,600 "
          "U.S. cities observed in the census years 1980, 1990, 2000 and 2010. Treatment: the city's racial "
          "segregation, measured by a multigroup entropy index from 0 to 100. Outcome: city direct general expenditure "
          "per resident, in dollars.",
    named="A researcher studies whether racial residential segregation lowers local public spending, using U.S. cities "
          "and the count of waterways as in Trounstine (AJPS 2016). Treatment: the city's racial segregation. Outcome: "
          "city direct general expenditure per resident.",
    cite="Trounstine (2016), AJPS 60(3): 709-725, doi:10.1111/ajps.12227",
    channel_cite="Hoxby (2000), American Economic Review 90(5): 1209-1238, doi:10.1257/aer.90.5.1209",
    base="waterways: number of rivers and streams that cross the city. Analyses include state-by-year fixed effects and "
         "control for log population. Each additional waterway raises the city's segregation index by 1.5 points on "
         "average.",
    implied="When school districts and municipalities in these metropolitan areas were drawn, streams served as their "
            "boundaries, so metropolitan areas whose cities have more waterways are divided into more separately governed "
            "school districts and municipalities.",
    consequence="The number of separate local governments can change city spending whatever the level of segregation.",
    link1="Each river or stream counted in waterways appears as a boundary stream in the state's 1920 boundary survey.",
    link2="When school districts and municipalities in these metropolitan areas were drawn, every boundary stream in the "
          "state's 1920 boundary survey became a jurisdiction line, so metropolitan areas whose cities have more such "
          "streams are divided into more separately governed school districts and municipalities.",
    bridge="1920 boundary survey",
    memo="Program memo (state municipal finance office, 2012): City finance data come from the Census of Governments and "
         "the Annual Survey of Government Finances. Direct general expenditure excludes utility and trust-fund spending. "
         "Segregation indices are computed from census block data.",
    others=["log_pop: log of city population.",
            "pct_black: Black share of the city population.",
            "pct_hisp: Hispanic share of the city population.",
            "med_income: city median household income.",
            "own_rate: share of housing units that are owner-occupied.",
            "region: census region."],
    alt="audit_grant: 1 if the city was drawn in the 1990 federal random draw that chose half of the eligible cities for "
        "a fair-housing testing grant, 0 otherwise; the grant paid a nonprofit, not the city government, to run "
        "paired-tester audits of landlords and lenders. Drawn cities have segregation indices 2.2 points smaller on "
        "average in later census years. The grant changed nothing else in drawn cities.",
    unit="city", topics=["housing", "police", "budget", "tax", "election", "employment", "transport", "parks"],
    treat="racial segregation", outcome="direct general expenditure per resident",
    plant_re=r"school districts|separately governed|fragment|tiebout|competing (?:local )?(?:jurisdiction|municipalit|government)",
)

N["preschool"] = dict(
    var="preschool_assign", alt_var="credit_waiver", design="rct", alt_scope="subset", source="polisci",
    study="A researcher studies whether graduating from high school raises adult voter turnout, using 123 children from "
          "low-income families in one Michigan school district who entered a randomized preschool study in 1962-1965 "
          "and were followed into adulthood. Treatment: graduated from high school by age 19. Outcome: voted in at least "
          "one general election from 1998 to 2008, from public voter files.",
    named="A researcher studies whether graduating from high school raises adult voter turnout, using the Perry Preschool "
          "experiment as in Sondheimer and Green (AJPS 2010). Treatment: high-school graduation. Outcome: adult turnout "
          "from voter files.",
    cite="Sondheimer and Green (2010), AJPS 54(1): 174-189, doi:10.1111/j.1540-5907.2009.00425.x",
    channel_cite="Holbein (2017), APSR 111(3): 572-583, doi:10.1017/S0003055417000119 (footnote 15); Heckman, Pinto and "
                 "Savelyev (2013), AER 103(6): 2052-2086, doi:10.1257/aer.103.6.2052",
    base="preschool_assign: 1 if the child was assigned by the study's random draw to two years of the study's half-day "
         "preschool program at ages 3 and 4, 0 if assigned to the control group. Assigned children are 19 percentage "
         "points more likely to graduate from high school by age 19.",
    implied="Teacher ratings collected by the study at ages 7 to 9 show that children assigned to the preschool program "
            "had fewer externalizing behavior problems and higher academic motivation than control children, and a "
            "separate 20-year school-based experiment that built these psychosocial skills raised adult voter turnout by "
            "11 to 14 percentage points.",
    consequence="The skills the program built can raise adult turnout whether or not the child graduates.",
    link1="Children assigned to the preschool program are listed as program children in the study's 1970 follow-up "
          "roster.",
    link2="Teacher ratings collected at ages 7 to 9 show that the program children in the 1970 follow-up roster had fewer "
          "externalizing behavior problems and higher academic motivation than the other children in the study, and a "
          "separate 20-year school-based experiment that built these psychosocial skills raised adult voter turnout by "
          "11 to 14 percentage points.",
    bridge="1970 follow-up roster",
    memo="Program memo (school district research office, 1999): The study enrolled five waves of children between 1962 "
         "and 1965. Follow-up interviews were held at ages 15, 19, 27 and 40. Voter-file matches use name and date of "
         "birth.",
    others=["female: 1 if female.",
            "iq_entry: Stanford-Binet IQ score at study entry.",
            "parent_educ: highest grade completed by either parent at study entry.",
            "father_home: 1 if the father lived in the home at study entry.",
            "ses_index: family socioeconomic index at study entry.",
            "birth_year: year of birth."],
    alt="credit_waiver: among students who reached 12th grade, 1 if the student was drawn in the district's random draw "
        "that waived one elective credit from the diploma requirement for half of each senior class, 0 otherwise; "
        "missing for students who did not reach 12th grade. Drawn students are 14 percentage points more likely to "
        "graduate by age 19. The waiver changed nothing else.",
    unit="participant", topics=["school", "family", "earnings", "employment", "arrest", "housing", "test", "welfare"],
    treat="high-school graduation", outcome="adult voter turnout",
    plant_re=r"externaliz|psychosocial|non-?cognitive|behavio(?:u)?r(?:al)? problem|academic motivation|socio-?emotional|"
             r"personality|self-regulat",
)

N["qob"] = dict(
    var="qob1", alt_var="building_draw", design="birth_timing", alt_scope="subset", source="classic",
    study="A researcher studies the earnings return to schooling, using about 330,000 men born in the United States in "
          "1930-1939, from the 1980 census 5 percent sample. Treatment: years of completed schooling. Outcome: log weekly "
          "wage in 1979.",
    named="A researcher studies the earnings return to schooling, using men born in 1930-1939 in the 1980 census and the "
          "quarter-of-birth design of Angrist and Krueger (QJE 1991). Treatment: years of schooling. Outcome: log weekly "
          "wage.",
    cite="Angrist and Krueger (1991), QJE 106(4): 979-1014, doi:10.2307/2937954",
    channel_cite="Buckles and Hungerman (2013), Review of Economics and Statistics 95(3): 711-724, "
                 "doi:10.1162/REST_a_00314",
    base="qob1: 1 if the man was born in January, February or March, 0 otherwise. School-entry rules set by birth date "
         "and compulsory schooling laws that allow leaving school at the 16th birthday mean that men born early in the "
         "year may leave school after fewer completed grades. Analyses include year-of-birth and state-of-birth fixed "
         "effects. Men born in the first quarter complete 0.13 fewer years of schooling on average.",
    implied="National birth-certificate records show that births in January, February and March are disproportionately "
            "to teenage and unmarried mothers.",
    consequence="Family background can change earnings whatever a man's years of schooling.",
    link1="Men born in January, February or March are coded as winter births in the census birth-quarter recode.",
    link2="National birth-certificate records show that births coded as winter births in the census birth-quarter recode "
          "are disproportionately to teenage and unmarried mothers.",
    bridge="census birth-quarter recode",
    memo="Program memo (census microdata office, 1983): The 5 percent sample is a stratified sample of housing units. "
         "Weekly wage is annual wage and salary income divided by weeks worked in 1979. Quarter of birth is recorded from "
         "the census questionnaire.",
    others=["black: 1 if the man reports his race as Black.",
            "married: 1 if currently married in 1980.",
            "smsa: 1 if living in a metropolitan area in 1980.",
            "region: census region of residence in 1980.",
            "birth_state: state of birth.",
            "age_1980: age in years on April 1, 1980."],
    alt="building_draw: among men born in the 80 rural counties of one state, 1 if the man's birth county was drawn in the "
        "state's 1944 random draw that gave 40 of these counties a new consolidated high school, 0 otherwise; missing "
        "for all other men. Men from drawn counties complete 0.5 more years of schooling on average. The draw changed "
        "nothing else in the drawn counties.",
    unit="respondent", topics=["employment", "earnings", "household", "housing", "migration", "military", "disability", "commute"],
    treat="years of schooling", outcome="log weekly wage",
    plant_re=r"\bteen(?:age|aged|agers?|s)?\b|unmarried|maternal|\bmothers?\b",
)

CALIBRATED = {'preschool': ('subset',
               'credit_waiver: among the students of the 1965 wave who reached 12th grade, 1 if the student was '
               "drawn in the district's random draw that waived one elective credit from the diploma requirement for "
               'half of that senior class, 0 otherwise; missing for all other students. Drawn students are 4 '
               'percentage points more likely to graduate by age 19, with a first-stage F-statistic of about 2. The '
               'waiver changed nothing else.'),
 'qob': ('subset',
         "building_draw: among men born in 1939 in 20 rural counties of one state, 1 if the man's birth county was "
         "drawn in the state's 1944 random draw that gave 10 of these counties a new consolidated high school, 0 "
         'otherwise; missing for all other men. Men from drawn counties complete 0.03 more years of schooling on '
         'average, with a first-stage F-statistic of about 2. The draw changed nothing else in the drawn counties.'),
 'rain_health': ('subset',
                 "transfer_draw: among households in the 6 villages of the fund's pilot area, 1 if the household's "
                 'village was drawn in the 1993 random draw by which a regional development fund chose 3 of these 6 '
                 'villages for an unconditional cash transfer paid to every household each quarter, 0 otherwise; '
                 'missing for households in the other 45 villages. Households in drawn villages have log income 0.02 '
                 'higher on average after the draw, with a first-stage F-statistic of about 2. The fund changed '
                 'nothing else in drawn villages.'),
 'rain_riot': ('subset',
               'works_draw: among the 16 districts of one state in 1993-1995, 1 if the district was drawn in the '
               '1992 random draw by which the state chose 8 of its 16 districts for a rural public-works program '
               'paying wages for road and pond construction, 0 otherwise; missing for districts in all other states '
               'and years. Drawn districts have rural income growth 0.2 percentage points higher on average, with a '
               'first-stage F-statistic of about 2. The program changed nothing else in drawn districts.'),
 'rain_vote': ('subset',
               'reminder_draw: among the 180 county-elections in the three states that ran a 1996-2000 pilot, 1 if '
               "the county was drawn in that election year's random draw for a nonpartisan mailed reminder of the "
               'election date and polling hours, sent to every registered voter in the county, 0 otherwise; missing '
               'for all other county-elections. Drawn counties have turnout 0.3 percentage points higher on average, '
               'with a first-stage F-statistic of about 4. The reminder named no candidate or party, and the draw '
               'changed nothing else in drawn counties.'),
 'waterways': ('subset',
               'audit_grant: among the 40 cities over 100,000 residents in the two states that took part, 1 if the '
               'city was drawn in the 1990 federal random draw that chose half of these cities for a fair-housing '
               'testing grant, 0 otherwise; missing for all other cities. The grant paid a nonprofit, not the city '
               'government, to run paired-tester audits of landlords and lenders. Drawn cities have segregation '
               'indices 0.3 points smaller on average in later census years, with a first-stage F-statistic of about '
               '2. The grant changed nothing else in drawn cities.')}
for _k, (_scope, _alt) in CALIBRATED.items():
    N[_k]["alt_scope"] = _scope
    N[_k]["alt"] = _alt

ORDER = list(N)
FAMOUS_THRESHOLD = 1000
CITES = {"rain_vote": (241, 41), "rain_riot": (184, 185), "rain_health": (49, 70), "waterways": (176, 1077),
         "preschool": (329, 1621), "qob": (2526, 537)}
for _k, (_a, _b) in CITES.items():
    N[_k]["famous"] = max(_a, _b) >= FAMOUS_THRESHOLD


@contextmanager
def registered(key):
    had = key in V.S
    old = V.S.get(key)
    V.S[key] = N[key]
    try:
        yield
    finally:
        if had:
            V.S[key] = old
        else:
            del V.S[key]


def agent_parts(key, version, arm="neutral", threat=True):
    with registered(key):
        return V.agent_parts(key, version, arm, threat)


def answer_key(key, version):
    with registered(key):
        return V.answer_key(key, version)


def parse_pick(key, t):
    with registered(key):
        return V.parse_pick(key, t)


def named_plant(key, t):
    with registered(key):
        return V.named_plant(key, t)


def outcome(key, version, t, fix_valid=False):
    with registered(key):
        return V.outcome(key, version, t, fix_valid=fix_valid)


prose = V.prose
