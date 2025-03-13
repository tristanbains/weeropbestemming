import os
import re
import datetime
import urllib.parse

def create_sitemap_xml(base_url,folder_build,priority='1.0',change_frequency='',print_xml=False):
    ps = [os.path.join(path, name) for (path, subdirs, files) in os.walk(folder_build) for name in files if name.endswith('index.html')]
    ps = [p.replace(folder_build,base_url) for p in ps]
    ps = [re.sub('(?<!\:)//','/',x) for x in ps]
    ps = [p.replace('index.html','') for p in ps]
    last_modification_date = datetime.date.today()
    xml_content = f'<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in ps:
        xml_content += f'\t<url>\n'
        xml_content += f'\t\t<loc>{urllib.parse.quote(p)}</loc>\n'
        xml_content += f'\t\t<lastmod>{last_modification_date.strftime("%Y-%m-%d")}</lastmod>\n'
        if change_frequency != '':
            xml_content += f'\t\t<changefreq>{change_frequency}</changefreq>\n'
        xml_content += f'\t\t<priority>{priority}</priority>\n'
        xml_content += f'\t</url>\n'
    xml_content += '</urlset>'
    if print_xml:
        print(xml_content)
    else:
        path_sitemap = os.path.join(folder_build,'sitemap.xml')
        print(path_sitemap)
        with open(path_sitemap,'w') as file:
            file.write(xml_content)


def create_robots_txt(base_url,folder_build,list_folder_exclude=[],print_txt=False):
    txt_content='User-agent: *\n'
    if len(list_folder_exclude)>0:
        txt_content += '\n'.join([f'Disallow: /{x}/' for x in list_folder_exclude]) + '\n\n'
    else:
        txt_content += 'Disallow:\n'
    txt_content += f"Sitemap: {os.path.join(base_url,'sitemap.xml')}"
    if print_txt:
        print(txt_content)
    else:
        path_robots = os.path.join(folder_build,'robots.txt')
        print(path_robots)
        with open(path_robots,'w') as file:
            file.write(txt_content)