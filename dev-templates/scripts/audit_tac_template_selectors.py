#!/usr/bin/env python3
"""Audit candidate TAC data selectors against both locked template DOMs."""
import argparse, json, pathlib, sys
import html5lib
import cssselect2

def count_matches(html, selector):
    parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder('etree'), namespaceHTMLElements=False, strict=False)
    root = parser.parse(html)
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    compiled = cssselect2.compile_selector_list(selector)
    return sum(1 for element in wrapped.iter_subtree() if any(s.pseudo_element is None and s.test(element) for s in compiled))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--registry', required=True)
    ap.add_argument('--monday', required=True)
    ap.add_argument('--weekdays', required=True)
    ap.add_argument('--report', required=True)
    args=ap.parse_args()
    reg=json.loads(pathlib.Path(args.registry).read_text(encoding='utf-8'))
    sources={'monday':pathlib.Path(args.monday).read_text(encoding='utf-8'),'weekdays':pathlib.Path(args.weekdays).read_text(encoding='utf-8')}
    results=[]
    for item in reg['selectors']:
        row={'name':item['name'],'selector':item['selector'],'kind':item['kind'],'templates':{}}
        for key,html in sources.items():
            actual=count_matches(html,item['selector'])
            expected=item[key]
            row['templates'][key]={'expected':expected,'actual':actual,'pass':actual==expected}
        results.append(row)
    report={'registry_version':reg['version'],'results':results,'pass':all(v['pass'] for r in results for v in r['templates'].values())}
    rendered=json.dumps(report,ensure_ascii=False,indent=2)
    pathlib.Path(args.report).write_text(rendered+'\n',encoding='utf-8')
    print(rendered)
    raise SystemExit(0 if report['pass'] else 1)

if __name__=='__main__': main()
