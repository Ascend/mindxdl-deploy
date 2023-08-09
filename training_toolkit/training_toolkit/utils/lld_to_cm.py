# coding: UTF-8

import os
import openpyxl


def read_excel():
    lld_excel = openpyxl.load_workbook("lld.xlsx")
    if lld_excel is None or len(lld_excel._sheets) < 13:
        return
    node_sheet = lld_excel._sheets[12]
    start_raw = 0
    node_list = []
    while start_raw < 10000:
        row_num = str(start_raw + 3)
        if node_sheet['A' + row_num].value is None or node_sheet['A' + row_num].value.find(u"服务器") != 0:
            break
        node_list.append({
            "tor_ip": node_sheet['B' + row_num].value,
            "server_ip": node_sheet['M' + row_num].value,
        })
        start_raw = start_raw + 1
    return node_list


def get_tor_list(node_list):
    tor_list = [[]]
    tor_ip = node_list[0]["tor_ip"]
    tor_id = 0
    for node in node_list:
        if tor_ip != node["tor_ip"]:
            tor_id = tor_id + 1
            tor_list.append([])
            tor_ip = node["tor_ip"]
        tor_list[tor_id].append(node)
    return tor_list


def handler():
    node_list = read_excel()
    tor_list = get_tor_list(node_list)
    yaml = open("basic-tor-node-cm.yaml", 'w')
    yaml.write("apiVersion: v1\n")
    yaml.write("kind: ConfigMap\n")
    yaml.write("metadata:\n")
    yaml.write("  name: basic-tor-node-cm\n")
    yaml.write("  namespace: volcano-system\n")
    yaml.write("data:\n")
    yaml.write("  tor_info: |\n")
    yaml.write("    {\n")
    yaml.write("      \"version\": \"1.0\",\n")
    yaml.write("      \"tor_count\": 4,\n")
    yaml.write("      \"server_list\": [\n")
    tor_id = 0
    for tor in tor_list:
        yaml.write("        {\n")
        yaml.write("          \"tor_id\": " + str(tor_id) + ",\n")
        tor_id = tor_id + 1
        yaml.write("          \"tor_ip\": \"" + str(tor[0]["tor_ip"]) + "\",\n")
        yaml.write("          \"server\": [\n")
        slice_num = 0
        for node in tor:
            yaml.write("            {\n")
            yaml.write("              \"server_ip\": \"" + str(node["server_ip"]) + "\",\n")
            yaml.write("              \"npu_count\": 8,\n")
            yaml.write("              \"slice_id\": " + str(slice_num) + ",\n")
            slice_num = slice_num + 1
            if slice_num == len(tor):
                yaml.write("            }\n")
            else:
                yaml.write("            },\n")
        yaml.write("          ]\n")
        if tor_id == len(tor_list):
            yaml.write("        }\n")
        else:
            yaml.write("        },\n")
    yaml.write("      ]\n")
    yaml.write("    }\n")
    yaml.close()
    os.system("kubectl apply -f basic-tor-node-cm.yaml")
    os.system("rm basic-tor-node-cm.yaml")
    os.system("kubectl get cm -A")

if __name__ == '__main__':
    handler()
