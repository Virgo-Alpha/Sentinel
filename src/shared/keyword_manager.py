"""
Keyword management system with fuzzy matching capabilities.

This module provides the KeywordManager class for loading and managing
target keywords used in the Sentinel cybersecurity triage system.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import ValidationError

from .models import KeywordConfig, KeywordsConfig

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class KeywordManager:
    """
    Manages target keywords for relevance assessment with fuzzy matching capabilities.
    
    Handles loading keyword configurations, categorization, and provides
    fuzzy matching for keyword variations and similar terms.
    """
    
    def __init__(self, config_path: Union[str, Path] = "config/keywords.yaml"):
        """
        Initialize the keyword manager.
        
        Args:
            config_path: Path to the keywords configuration YAML file
        """
        self.config_path = Path(config_path)
        self._config: Optional[KeywordsConfig] = None
        self._keywords_by_category: Dict[str, List[KeywordConfig]] = {}
        self._all_keywords: List[KeywordConfig] = []
        self._keyword_lookup: Dict[str, KeywordConfig] = {}
        self._variation_lookup: Dict[str, KeywordConfig] = {}
        
    def load_config(self) -> KeywordsConfig:
        """
        Load and validate the keywords configuration from YAML file.
        
        Returns:
            KeywordsConfig: Validated configuration object
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            if not self.config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                
            # Validate and parse configuration
            self._config = self._parse_keywords_config(raw_config)
            self._build_indexes()
            
            total_keywords = len(self._all_keywords)
            total_variations = sum(len(kw.variations) for kw in self._all_keywords)
            
            logger.info(
                f"Loaded {total_keywords} keywords with {total_variations} variations "
                f"from {self.config_path}"
            )
            return self._config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {self.config_path}: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _parse_keywords_config(self, raw_config: Dict) -> KeywordsConfig:
        """Parse and validate raw keywords configuration data."""
        if not isinstance(raw_config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # Expected keyword categories
        expected_categories = [
            'cloud_platforms', 'security_vendors', 'enterprise_tools',
            'enterprise_systems', 'network_infrastructure', 'virtualization',
            'specialized_platforms'
        ]
        
        parsed_categories = {}
        
        for category in expected_categories:
            category_data = raw_config.get(category, [])
            if not isinstance(category_data, list):
                raise ConfigurationError(f"Category '{category}' must be a list")
            
            keywords = []
            for i, keyword_data in enumerate(category_data):
                try:
                    if not isinstance(keyword_data, dict):
                        raise ValidationError(f"Keyword {i} must be a dictionary")
                    
                    # Validate required fields
                    if 'keyword' not in keyword_data:
                        raise ValidationError("Keyword field is required")
                    
                    # Validate weight range
                    weight = keyword_data.get('weight', 1.0)
                    if not 0.0 <= weight <= 1.0:
                        raise ValidationError(f"Weight must be between 0.0 and 1.0, got {weight}")
                    
                    keyword_config = KeywordConfig(**keyword_data)
                    keywords.append(keyword_config)
                    
                except (ValidationError, ValueError) as e:
                    raise ConfigurationError(
                        f"Invalid keyword configuration in category '{category}' at index {i}: {e}"
                    )
            
            parsed_categories[category] = keywords
        
        # Parse settings and categories
        settings = raw_config.get('settings', {})
        categories = raw_config.get('categories', {})
        
        return KeywordsConfig(
            **parsed_categories,
            settings=settings,
            categories=categories
        )
    
    def _build_indexes(self) -> None:
        """Build internal indexes for fast keyword lookups."""
        if not self._config:
            return
        
        self._keywords_by_category.clear()
        self._all_keywords.clear()
        self._keyword_lookup.clear()
        self._variation_lookup.clear()
        
        # Build category-based index
        for category_name in [
            'cloud_platforms', 'security_vendors', 'enterprise_tools',
            'enterprise_systems', 'network_infrastructure', 'virtualization',
            'specialized_platforms'
        ]:
            category_keywords = getattr(self._config, category_name, [])
            self._keywords_by_category[category_name] = category_keywords
            self._all_keywords.extend(category_keywords)
        
        # Build lookup indexes
        for keyword_config in self._all_keywords:
            # Primary keyword lookup
            key = keyword_config.keyword.lower()
            self._keyword_lookup[key] = keyword_config
            
            # Variation lookup
            for variation in keyword_config.variations:
                var_key = variation.lower()
                self._variation_lookup[var_key] = keyword_config
    
    def get_keywords_by_category(self, category: str) -> List[KeywordConfig]:
        """
        Get all keywords for a specific category.
        
        Args:
            category: Category name (e.g.ttings.senfig self._corn retu   fig()
    on.load_c  self      :
    elf._config    if not s""
     "
       gsching settinkeyword mationary of       Dict   ns:
   tur    Re  
    
      tings.ching setmatyword  Get ke  """
        
     f) -> Dict:selngs(f get_setti    
    de)
ig(_confoadself.l    return lear()
    up.c_look_variation     self.  .clear()
 yword_lookup   self._ke)
     r(ywords.cleakef._all_    sel
    ()learcategory.cywords_by__ke       self.ne
 onfig = Nolf._c
        se     """
   objectation ed configurload      Re:
      urns     Ret          
 .
from fileuration  configoad      Rel  
     """fig:
   rdsConf) -> Keywoelad_config(s    def relo  

  sues   return is     
        
_issuescategoryame] = _nes[categoryssu         i    
   s:suegory_iscate     if       
              )
                  "
 t}fig.weigheyword_con}': {kywordconfig.keword_ for '{keyweightf"Invalid                         es.append(
ory_issu      categ             
 ght <= 1.0:weiig.keyword_conft 0.0 <=     if no          ange
  ht rheck weig  # C       
                     )
  fig.keywordkeyword_connames.add(ord_eyw   k            d}")
 orfig.keyword_coneyw {krd:icate keywo"Duplpend(fissues.apry_atego          c  :
        eyword_namesyword in kfig.ke_conyword    if ke     
       rytego within cadsicate keyworplr du # Check fo         rds:
      keywon g iord_confior keyw      f
                  ()
es = setrd_nam    keywo       []
 y_issues =    categor         ):
ms(.itegoryds_by_cateorelf._keywin s keywords gory_name,   for cate   
        {}
   issues =       
     nfig()
    oad_co  self.l
          :fig_conif not self.
        ""      "
   issuesvalidationists of ries to lg category mappin    Dictiona  ns:
      ur     Ret      
   
  ssues.ny in aur rets andigurationconford eyw all kidateal
        V"""        ist[str]]:
[str, LDictself) -> ords(alidate_keyw def vs
    
   return stat    
    }
              
      keywords)in w or kriations) f(len(kw.vaations': sum       'vari       ,
  ywords) len(ke    'count':          
   {name] =][category_ies'ats['categorst          tems():
  y_category.iwords_bn self._keys i keywordtegory_name, for ca  
            }
    : {}
     ories'   'categ       s),
  keywordn self._all_ns) for kw iw.variatio': sum(len(kvariations 'total_         ywords),
  self._all_keords': len(tal_keyw        'to= {
    s   stat        
    ()
  d_configelf.loa          sonfig:
  ._ct self  if no""
        "      cs
istiord stath keywionary wit Dict    s:
       rn       Retu
        
 .ded keywordsloat boutics at statis  Ge"
      ""        :
 int]]]ct[str,[int, Distr, Unionlf) -> Dict[(se_statisticseyword def get_k   
   ches
 n final_mat     retur   
              )
 rue
 e=T  revers         eight'],
 '] * x['w['confidence: xbda x    key=lam     ort(
   hes.s_matc       finalalues())
 tches.vque_ma list(unil_matches =ina fre
       coe sonfidenc chtedort by weig S
        #    atch
    key] = mtches[_maque    uni       
     nce']:['confidekey]e_matches['] > uniqu['confidencematches or e_match in uniquot key n         ifd']
   wor'key= match[     key      tches:
   in machfor mat       {}
  ches =  unique_mat
      atches)exact ms (prefer teuplica  # Remove d    
         _matches)
 tend(fuzzyches.ex   mat       xt)
  tches(ted_fuzzy_mas = self.finy_matchezzfu          uzzy:
  clude_f       if in enabled
 tches ifGet fuzzy ma        #   
es)
      tchact_mand(exs.exte    matche(text)
    t_matchesf.find_exac= selhes   exact_matches
      matcet exact # G              

  es = [] match       "
        ""ht
nce and weigd by confidehes sorte all matc List of      
        Returns:        
  hes
       matc fuzzy include to hetherude_fuzzy: W      inclords
      eywor k to search fText  text:         
       Args: 
      xt.
    in tey)  fuzzt andatches (exacrd mwoeynd all k     Fi """
     ]]]:
      int, float[str,onstr, Uniict[> List[D = True) - boolzy:uzde_fclu: str, inself, textds(wormatch_keyef     
    dwn'
knorn 'un       retue
 namory_teg  return ca            eywords:
  in kg yword_confif ke   i        :
 ry.items()s_by_catego._keywords in selford, keywnameategory_     for c""
   ration."d configuwor keye for aory namege catGet th"""         str:
 ->fig) KeywordConord_config:keywf, gory(selkeyword_catet_ def _ge
    
   row[-1]s_urn previou       ret 
 
       urrent_rowrow = crevious_      p    
  itutions)), subst deletionsrtions,in(inseppend(mt_row.a      curren          (c1 != c2)
us_row[j] + = previoions substitut        
        row[j] + 1s = current_on      deleti
           + 1] + 1[jous_rowns = previtio       inser         (s2):
numerate ec2 in     for j,   
     ow = [i + 1]rrent_r     cu       :
ate(s1)1 in enumer  for i, c    ) + 1))
  len(s2t(range(lisious_row =   prev    
      1)
    n(s   return le      0:
   =  len(s2) =        if
     
   ), s1_distance(s2tein_levenshn self.  retur         (s2):
 s1) < lenlen(f  i"
       "gs."trinwo seen tetwdistance bein edit shtculate Leven"""Cal      > int:
  r) -s2: str, elf, s1: stce(sn_distanei_levensht def    s
    
atchereturn m
        
                  })         stance
 tance': diedit_dis '                       ig),
nf_cokeywordd_category(yworelf._get_ke': segory    'cat                    ght,
ig.weiword_confeight': key       'w                
 nce,: confideidence' 'conf                  ],
     ': [context'contexts                  : 1,
      unt'   'hit_co               
      rase_text,rm': phhed_tematc  '                     .keyword,
 nfigrd_cowokeyeyword':  'k                {
       .append(tches ma                 
                     d])
 context_ent_start:ntexords[co'.join(wcontext = '                    + 5)
 term_words) n(), i + len(len(words mit_end =   contex                  - 5)
(0, imax_start =      context            
   ence:min_confidnce >=  if confide          
                    t)))
 texn(term_se_text), len(phramax(lence /  (dista0 -idence = 1.onf c            ance:
   phrase_dist<= max_if distance                 
        length
for phrase  Scale rm_words)  #len(tee * x_distanctance = mahrase_disax_p      m
      rm_text)ase_text, tedistance(phrtein_elf._levensh = s    distance             
  s)
     _wordn(term ' '.joiext =    term_t     
   hrase)(p' '.joinrase_text =     ph        
)]rdslen(term_woi + rds[i:hrase = wo          ps) + 1):
  rdlen(term_wods) - worrange(len(or i in  
        f []
       es =  match"
      "hrases."word pulti- for mzzy matches"Find fu""       ]:
 ct) -> List[Die: floatonfidencin_c          m                          
nt,distance: ionfig, max_: KeywordCfigword_conkey                                  str], 
 List[s: ], term_wordtr: List[s, wordses(selfchatfuzzy_mase_d_phr   def _fin   
 ue)
 , reverse=Trnfidence']: x['co=lambda xkeylues(), .vaique_matchesed(unrtreturn so      
      
    atchy] = mes[kee_matchiqu    un          e']:
  ]['confidenc_matches[key unique >nfidence']r match['cotches on unique_ma key not i    if
        ched_term']), match['matrd']['keywo(match =     key
         matches:tch inr ma      fos = {}
  tchemanique_   u
     fidencesort by cond uplicates anRemove d      #  
  })
                               
        cee': distandistancit_        'ed                           onfig),
 d_cywory(ke_categorget_keyword self._':orycateg  '                          
        ,ig.weightrd_conf keywo':   'weight                            
     dence,e': confidencnfi'co                            ],
        [contextcontexts':           '                     1,
      unt':cot_hi       '                          
   erm': word,matched_t     '                               g.keyword,
eyword_confiord': k      'keyw                        ({
      s.append      matche                        
                                 end])
 t:context_ontext_stars[cordoin(w ' '.jtext =     con                           s), i + 6)
len(word= min(context_end                          )
       x(0, i - 5rt = matantext_s      co                    :
      fidencen_conce >= mifiden con         if                       
                   
     term)))n(), lelen(word/ max(ance diste = 1.0 - ( confidenc                        matches
   ort id very sh:  # Avoterm) > 2ce and len(distanmax_= stance < di if                     
  , term)rd_distance(wo_levenshteince = self.tanis  d                  
    ate(words):mer in enuword for i,                   ing
 y matchzz word fugle Sin       #              else:
              
   ))           nce
       fidece, min_conistang, max_dd_confi, keywor_words words, term             
          atches(se_fuzzy_mfind_phra._(selfhes.extend       matc             rds) > 1:
len(term_wo   if             s
 chemat phrase , look forms-word terultir m# Fo          
                 it()
     plrm.s_words = te      term         
 ch_terms: sear for term in               
 ])
       ionsiatnfig.vareyword_co in kr ver() foxtend([v.lowrch_terms.e         seaer()]
   rd.lowonfig.keywo [keyword_ch_terms = searc          
 words:key_all_self.ig in rd_confywo keor
        f   
     t()splir().lowerds = text. wo]
        matches = [ 
             ', 0.7)
 onfidenceet('min_cngs.gsettif._config. = selncede_confimin  
              e', 2)
distancedit_ax_t('mttings.geseelf._config. sx_distance =         maone:
   e is Nax_distanc      if m    
     return []
            ue):
 g', Try_matchin_fuzzlegs.get('enabing.settconfinot self._     if d
    enablematching isk if fuzzy     # Chec      
    ig()
  _conf self.load      nfig:
     ._co if not self   "
       ""
     idenceonfexts, and cunt, contrd, hit_co with keywoctionariesatch di  List of m         
    Returns:           
 g
     zy matchinuz fdistance fort m edi Maximux_distance:     ma
       r keywords fochxt to sear    text: Te  s:
            Arg         
distance.
 dit ng ein text usimatches y keyword nd fuzz
        Fi     """  t]]]:
 nt, floa[str, itr, Union List[Dict[s -> None) int =x_distance:: str, ma(self, textzy_matchesfind_fuz   def es
    
 eturn match   r    
        ons
 ati varick don't cheis keyword,h for th# Found matcak          bre             })
                   g)
d_confikeywory(word_categorlf._get_key seory':     'categ               t,
    .weighfigeyword_conight': k      'we             tch
      Exact ma': 1.0,  #dence    'confi               
     ts,contex: ntexts'  'co                    ),
  onsositilen(hit_p_count': it 'h               ,
        : term_term'atched   'm                
     rd,fig.keywocond': keyword_   'keywor                   ({
  appendtches.        ma                    
     
       d(context)en.appxts conte               )
        _idx]x:endrds[start_id'.join(woontext = '      c                   
window + 1)xt_s + conteord_pords), wn(wodx = min(le_i       end              indow)
   t_w contex -os(0, word_p = max_idxartst                        1
it()) - xt[:pos].splpos = len(te   word_              n
       extractioontext for cdex ind word in # F                       positions:
s in hit_ po      for                    
         it()
     splrds = text.  wo              []
     ts =  contex                   matches
und aroct contexts Extra           #         sitions:
it_po  if h             
              
   s + 1t = po   star               pos)
      ppend(s.aionositt_p         hi              break
                    
          pos == -1: if                      , start)
 arch_termxt.find(seh_te searc     pos =                 e True:
        whil             0
  start =              []
      ositions = t_p          hi        tching
   mastring# Simple sub                  
      else:        
    s_found]che m in mat forrt()= [m.staositions     hit_p         0)
       e else ivsensite_asSE if not cCAre.IGNOREext, rch_tattern, seaditer(pfine.es_found = ratch     m           b'
    term) + r'\search_escape( re.'\b' +pattern = r                hing
    ary matcword bound Use  #          :
         ord_boundaryif w             
            
       lower()lse term.e esitiv if case_sen_term = term      search        erms:
  h_tin searcterm         for    
    
         ions)ariatig.v_confeyword.extend(krch_terms      seaord]
      _config.keyw = [keywordrmsh_te     searc      
 ywordprimary ke   # Check         
 eywords:l_k in self._aligonfr keyword_c  fo 
      
        10)w',ndontext_wiet('cotings.g._config.setdow = selfwint_   contex)
     ching', Trueary_matd_boundget('worsettings.fig. self._cond_boundary =   wor
     ingtching settoundary mard bWo      #        
  lower
 text_else nsitive t if case_seextext = t  search_lse)
      , Fa_sensitive'seet('cattings.gonfig.self._ctive = se  case_sensi     ng
 ettity sitivie sensas for c # Check   
       r()
     = text.lowetext_lower       = []
        matches      
   )
  onfig(_c self.load         :
  configf._ot sel     if n""
     "   
   onfidence, and ctexts con hit_count,th keyword,s wiriech dictionaist of mat     L  urns:
       Ret 
              
   for keywordst to search xt: Tex        teArgs:
               
      text.
d matches inyworxact ke   Find e       """
 :
     nt, float]]]r, i, Union[stt[Dict[strstr) -> Lisext:  telf,es(s_exact_match   def find
    
     ]_names
    keywordigh_n hw.keyword i     if krds
       keywoall_ self._w infor k  kw    [
        turn  re
      ])('high', [tegories.get_config.caelf. ses =amword_nkeyhigh_
        
        ig()load_confelf.      sg:
      _confit self.f no  i""
            "  rds
y keywooritri phigh    List of     
     Returns:       
   
     iority.d as high prrkeds ma  Get keywor
      """       Config]:
 st[KeywordLilf) -> words(se_keypriority get_high_
    def        ]
s
    ameword_n_keyticaln crieyword i if kw.k           s
rdkeywo self._all_w inr kw fo          k  [
n ur ret
       ', [])et('criticalries.gig.categof._confel ses =keyword_namritical_   c     
       ig()
 conf self.load_      
     ._config:elf    if not s   
    """ords
     ty keywical prioriList of crit             Returns:
   
       ty.
     tical priorid as criwords marke Get key       "
""
        dConfig]:st[Keyworf) -> Liywords(sel_critical_ke   def gets
    
 keyword self._all_    returnfig()
    .load_con       self:
     onfigot self._cif n  
      """     ions
   figuratd coneyworst of all k     Lis:
            Return    
   tions.
    uraigeyword confet all k
        G """     :
  ig]ywordConf> List[Ke) -rds(selfll_keywot_a
    def ge   
 y, [])gory.get(categorrds_by_cateywolf._kereturn se  ig()
      oad_conflf.l         seig:
   f._conf  if not sel
      ""  "     gory
 the cateations for ur configwordist of key  L    
      Returns:            
     rs')
   rity_vendo'secuatforms', pl, 'cloud_