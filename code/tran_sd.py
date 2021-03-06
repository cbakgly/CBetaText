#!/usr/bin/env python
# vim: set fileencoding=utf-8
import json
import linecache

import pymysql

jsonfile = open("txt/gaiji.json")
gaiji_dict = json.load(jsonfile)
key_type = []
statistic_file = open('txt/statistic.txt','w')
statistic_file.write("原始数据文件：char-freq.csv\n汉字及字数文件:unicode.txt\n非汉字及组字式文件:no_unicode.txt\n正字化数据文件，包括正字，狭义异体字对应的正字以及广义异体字:std.txt\n异体字数据文件:variants.txt\n异体字与正字对应文件:replaced.txt\n最终结果文件:final_data.txt\n最终结果详细信息:detail_final_data.txt\n字数及字表节点信息：\n")
def get_json_key_type(gaiji_dict):
    #获取代码对应的字符种类
    for gaiji in gaiji_dict.values():
        for gaiji_ele in gaiji.keys():
            if gaiji_ele in key_type:
                pass
            else:
                key_type.append(gaiji_ele)
    jsonfile.close()
    return key_type
key_types = [ u'unicode-char', u'normal', u'normal_unicode', u'char_in_siddham_font', u'rjchar',u'zzs']

def trans_key(line_key):
    #将代码转换为字或者組字式
    if line_key in gaiji_dict.keys():
        line_value = gaiji_dict[line_key]
        result = line_key
        for key_type in key_types:
            if key_type in line_value.keys():
                result = (key_type,line_value[key_type])
                break
    else:
        result = ('no_gaiji',line_key)
    return result

def trans_line(freq_line):
    #对文本行进行转换
    line_splited = freq_line.split(",")
    replaced_cb = trans_key(line_splited[0])
    line_splited[0] = replaced_cb[1]
    line_splited.insert(0,replaced_cb[0])
    return line_splited

def trans_char_freq():
    #将原始数据分割为unicode汉字其他（包括非汉字和組字式）
    freq_file = open("txt/char-freq.csv","r")
    unicode_file = open("txt/unicode.txt","w")
    unicode_file.write('type,char,frequency\n')
    no_unicode_file = open("txt/no_unicode.txt","w")
    no_unicode_file.write('type,char,frequency\n')

    for freq_line in freq_file.readlines()[1:]:
        transed_line = trans_line(freq_line)
        data = ",".join(transed_line)
        hanzi_char = transed_line[1]
        #print (hanzi_char)
        if transed_line[0] is 'zzs' or len(hanzi_char)!=1:
            no_unicode_file.write(data)
        else:
            char_no = ord(transed_line[1])
            if (char_no>=0xf900 and char_no <=0xfad9) or \
                (char_no>=0x4e00 and char_no<=0x9fbf) or \
                (char_no>=0x3400 and char_no <=0x4dbf) or \
                (char_no>=0x20000 and char_no <=0x2fa1f):
                unicode_file.write(data)
            else:
                no_unicode_file.write(data)
    unicode_file.close()
    no_unicode_file.close()
    freq_file.close()



def get_std_hanzi(conn, variant):
    #查询正字
    if variant:
        try:
            cur = conn.cursor()
            cur.execute('SELECT source, std_hanzi FROM lqhanzi.lq_hanzi_set where hanzi_char = "'+variant+'" and std_hanzi<>""')
            selectResultList = cur.fetchall()
            return selectResultList
            cur.close()
            raise "Mysql Error %d: %s" % (e.args[0], e.args[1])
        except:
            return False

def transfer_tuple_to_list(tuple_thing):
    #将元组转换为列表
    list_thing = []
    for ele in tuple_thing:
        if type(ele) is not tuple:
            list_thing.append(str(ele))
        else:
            list_thing.extend(transfer_tuple_to_list(ele))
    return list_thing

def rep_std():
    #将狭义异体字替换为正字
    conn = pymysql.connect(host='192.168.16.3', user='lq', passwd='123456', db='lqhanzi', port=3306, charset='utf8mb4')
    n = m = 1
    origin_unicode_file = open("txt/unicode.txt", "r")
    variant_file = open('txt/variants.txt', "w")
    variant_file.write('char;	count;	type,std_chars\n')
    std_file = open("txt/unicode_types.txt", "w")
    std_file.write('type,char,char_freq\n')

    for ori_line in origin_unicode_file.readlines()[1:]:
        splited_line = ori_line.split(',')
        hanzi_char = splited_line[1]

        std_list = get_std_hanzi(conn, hanzi_char)

        is_variant = False
        if std_list:
            is_variant = False
            for result_row in std_list:
                if result_row[1].find(hanzi_char) > -1:
                    is_variant = False
                    break
                else:
                    is_variant = True
        if is_variant:
            #print (n)
            n += 1
            stds = transfer_tuple_to_list(std_list)
            std_str = ":".join(stds)
            if std_str.find(";") > -1:
                std_file.write("mul_vt,")
                std_file.write(hanzi_char+",")
                std_file.write(splited_line[2])
            else:
                std_file.write("single_vt,")
                std_file.write(stds[1] + ",")
                std_file.write(splited_line[2])
            variant_file.write(hanzi_char+";  ")
            variant_file.write(splited_line[2].replace("\n","")+";  ")
            variant_file.write(",".join(stds)+"\n")

        else:
            #print (m)
            m += 1
            std_file.write("std,")
            std_file.write(hanzi_char+",")
            std_file.write(splited_line[2])
    conn.close()
    origin_unicode_file.close()
    variant_file.close()
    std_file.close()

def sort_by_value(d):
    items=d.items()
    backitems=[[v[1],v[0]] for v in items]
    backitems.sort()
    return [ backitems[i][1] for i in range(0,len(backitems))]

def statistic():
    std_file = open('txt/unicode_types.txt', "r")
    final_file = open("txt-withoutzzs/final_char_freq.txt", "w")
    detail_final_file = open("txt-withoutzzs/detail_final_char_freq.txt", "w")
    no_unicode_file = open('txt/no_unicode.txt','r')


    combined = {}
    #total_no = 206800574.0
    total_no = 0.0
    no_unicode_num = 0

    for st_line in std_file.readlines()[1:]:
        splited_line = st_line.split(",")
        hanzi_char = splited_line[1]
        hanzi_no = int(splited_line[2])
        total_no += hanzi_no
        if hanzi_char in combined.keys():
            combined[hanzi_char][0] += hanzi_no
            combined[hanzi_char][1].extend(splited_line)
        else:
            combined[hanzi_char] = [hanzi_no,splited_line]

    for st_line in no_unicode_file.readlines()[1:]:
        splited_line = st_line.split(",")
        hanzi_char = splited_line[1]
        hanzi_no = int(splited_line[-1])
        #print(splited_line)
        if splited_line[2].find('t')>-1:
            pass
        else:
            #print(splited_line)
            hanzi_no = int(splited_line[-1].replace('\n',''))
        no_unicode_num += hanzi_no


    statistic_file.write('汉字总数:' + str(int(total_no)) + "\n")
    statistic_file.write('非unicode字符及組字式字数:' + str(no_unicode_num) + "\n")
    combined = sorted(combined.items(), key = lambda d: d[1][0])

    r_combined = reversed(combined)
    for line_no, line in enumerate(r_combined):
        #print(line)
        final_file.write(line[0] + ",")
        detail_final_file.write(line[0] + ",")
        final_file.write(str(line[1][0]) + "\n")

        detail_final_file.write(str(line[1][0]) + ";")
        for t_tuple in line[1][1:]:
            detail = ",".join(t_tuple)
            detail = detail.replace("\n", "")
            detail_final_file.write(detail + ";")
        detail_final_file.write("\n")


    r_combined = reversed(combined)
    table_data = [v[1][0] for v in r_combined]
    first = True
    second = True
    for data_no, data in enumerate(table_data):

        cover_ratio = sum(table_data[:data_no])/total_no
        if data_no > 500:
            add_ratio = sum(table_data[data_no-500:data_no])/total_no
            #print (data_no,":", cover_ratio,":", add_ratio)
        if cover_ratio >= 0.999 and add_ratio < 0.0001 and first:
            print ("first",data_no)
            statistic_file.write('一级字表节点:' + str(data_no) + "," + linecache.getline('txt-withoutzzs/final_char_freq.txt', data_no))
            first = False
        if cover_ratio >= 0.995 and add_ratio < 0.002 and second:
            print ("second",data_no)
            statistic_file.write('二级字表节点:' + str(data_no) + "," + linecache.getline('txt-withoutzzs/final_char_freq.txt', data_no))
            second = False


    std_file.close()
    final_file.close()
    detail_final_file.close()

def statistic2():
    std_file = open('txt/unicode_types.txt', "r")
    final_file = open("txt/final_char_freq.txt", "w")
    detail_final_file = open("txt/detail_final_char_freq.txt", "w")
    no_unicode_file = open('txt/no_unicode.txt','r')


    combined = {}
    total_no = 0.0
    zzs_no = 0
    no_unicode_num = 0

    for st_line in std_file.readlines()[1:]:
        splited_line = st_line.split(",")
        hanzi_char = splited_line[1]
        hanzi_no = int(splited_line[2])
        total_no += hanzi_no

        if hanzi_char in combined.keys():
            combined[hanzi_char][0] += hanzi_no
            combined[hanzi_char][1].extend(splited_line)
        else:
            combined[hanzi_char] = [hanzi_no,splited_line]

    for st_line in no_unicode_file.readlines()[1:]:
        splited_line = st_line.split(",")
        hanzi_char = splited_line[1]
        hanzi_no = int(splited_line[-1].replace('\n',''))
        #print(splited_line)
        if splited_line[2].find('t')>-1:
            pass
        elif splited_line[0] == 'zzs':
            #print ('zzs')
            total_no += hanzi_no
            zzs_no += hanzi_no
            if hanzi_char in combined.keys():
                combined[hanzi_char][0] += hanzi_no
                combined[hanzi_char][1].extend(splited_line)
            else:
                combined[hanzi_char] = [hanzi_no, splited_line]
        else:
            no_unicode_num += hanzi_no


    statistic_file.write('\n汉字(含组字式)总数:' + str(int(total_no)) + "\n")
    statistic_file.write('非unicode字符字数:' + str(no_unicode_num) + "\n")
    combined = sorted(combined.items(), key = lambda d: d[1][0])

    r_combined = reversed(combined)
    for line_no, line in enumerate(r_combined):
        #print(line)
        final_file.write(line[0] + ",")
        detail_final_file.write(line[0] + ",")
        final_file.write(str(line[1][0]) + "\n")

        detail_final_file.write(str(line[1][0]) + ";")
        for t_tuple in line[1][1:]:
            detail = ",".join(t_tuple)
            detail = detail.replace("\n", "")
            detail_final_file.write(detail + ";")
        detail_final_file.write("\n")


    r_combined = reversed(combined)
    table_data = [v[1][0] for v in r_combined]
    first = True
    second = True
    for data_no, data in enumerate(table_data):

        cover_ratio = sum(table_data[:data_no])/total_no
        if data_no > 500:
            add_ratio = sum(table_data[data_no-500:data_no])/total_no
            #print (data_no,":", cover_ratio,":", add_ratio)
        if cover_ratio >= 0.999 and add_ratio < 0.0001 and first:
            print ("first",data_no)
            statistic_file.write('一级字表节点:' + str(data_no) + "," + linecache.getline('txt/final_char_freq.txt', data_no))
            first = False
        if cover_ratio >= 0.995 and add_ratio < 0.002 and second:
            print ("second",data_no)
            statistic_file.write('二级字表节点:' + str(data_no) + "," + linecache.getline('txt/final_char_freq.txt', data_no))
            second = False


    std_file.close()
    final_file.close()
    detail_final_file.close()
    statistic_file.close()

'''def get_total_no(txt_file):
    total_no = 0
    first_line = txt_file.getline(0)
    #if type(first_line[0])
    for freq_line in freq_file.readlines()[1:]:
        transed_line = trans_line(freq_line)
        ori_total_no += int(transed_line[-1])'''

def check_freq_sum():
    freq_file = open("txt/char-freq.csv", "r")
    final_file = open("txt/final_char_freq.txt", "r")
    no_unicode_file = open('txt/no_unicode.txt', 'r')

    ori_total_no = 0
    final_total_no = 0
    no_total_no = 0

    for freq_line in freq_file.readlines()[1:]:
        transed_line = trans_line(freq_line)
        ori_total_no += int(transed_line[-1])

    for final_line in final_file.readlines():
        transed_line = trans_line(final_line)
        final_total_no += int(transed_line[-1])

    for no_line in no_unicode_file.readlines()[1:]:
        transed_line = trans_line(no_line)
        no_total_no += int(transed_line[-1])

    print("freq no: %d,final total no :, %d" % (ori_total_no, final_total_no+no_total_no))

#trans_char_freq()
#rep_std()
statistic()
statistic2()
#check_freq_sum()