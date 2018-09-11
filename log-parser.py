import re
import time
import datetime
from matplotlib import pyplot as plt


def parse_item(content_msg):
    pattern = "===============================================================\ncommit comment:.*?==============================================================="
    pattern = re.compile(pattern, re.DOTALL)
    return pattern.findall(content_msg)


def parse_bug_type(bug_item):
    pattern = r"Bug type: (.*)"
    pattern = re.compile(pattern)
    return pattern.findall(bug_item)


def calculate_time_gap(target_range):
    start_date, end_date = target_range.split("-")
    time_pattern = "%Y/%m/%d %H:%M:%S"
    start_date = time.mktime(time.strptime(start_date, time_pattern))
    end_date = time.mktime(time.strptime(end_date, time_pattern))
    start_date = datetime.datetime.fromtimestamp(start_date)
    end_date = datetime.datetime.fromtimestamp(end_date)
    result_hrs = end_date - start_date
    return result_hrs.days, result_hrs.seconds / 3600


def parse_bug_effort(bug_item):
    comment_pattern = r"commit comment:\s*(?P<comment>\w[^\n]+)"
    comment_pattern = re.compile(comment_pattern)
    comment_content = comment_pattern.findall(bug_item)[0]
    effort_pattern = r"Bug effort: (?P<effort>[^\n]+)"
    effort_pattern = re.compile(effort_pattern)
    effort_content = effort_pattern.findall(bug_item)[0]
    effort_content = effort_content.split("::")
    time_range = effort_content[0]
    version_iter = effort_content[1]
    return [comment_content, calculate_time_gap(time_range), version_iter]


def add_count(target_dict, current_arr):
    if len(current_arr) == 1:
        if current_arr[0] not in target_dict:
            target_dict[current_arr[0]] = 1
        else:
            target_dict[current_arr[0]] += 1
        return
    if current_arr[0] not in target_dict:
        target_dict[current_arr[0]] = dict()

    add_count(target_dict[current_arr[0]], current_arr[1:])


def construct_statistic_dict(target_lst):
    target_dict = dict()
    for single_item in target_lst:
        current_arr = single_item.split("::")
        add_count(target_dict, current_arr)
    return target_dict


def count_whole_tree(target_dict):
    if type(target_dict) != type(dict()):
        return target_dict
    all_nodes = 0
    for key in target_dict:
        all_nodes += count_whole_tree(target_dict[key])
    return all_nodes


def calculate_whole_tree(target_dict):
    new_dict = dict()
    for key in target_dict:
        new_dict[key] = count_whole_tree(target_dict[key])
    return new_dict


def count_tree_leaf(target_dict):
    def merge_dict(dict_one, dict_two):
        for single_key in dict_two:
            if single_key not in dict_one:
                dict_one[single_key] = dict_two[single_key]
            else:
                dict_one[single_key] += dict_two[single_key]

    if type(target_dict) != type(dict()):
        return None
    result_dict = dict()
    for key in target_dict:
        current_item = target_dict[key]
        if type(current_item) != type(dict()):
            if key not in result_dict:
                result_dict[key] = current_item
            else:
                result_dict[key] += current_item
        else:
            tmp_result_dict = count_tree_leaf(current_item)
            merge_dict(result_dict, tmp_result_dict)
    return result_dict


def analysis_log_file(file_name):
    content = open(file_name, 'r').read()
    result_lst = parse_item(content)
    result_lst = [parse_bug_type(bug_item)[0] for bug_item in result_lst if len(parse_bug_type(bug_item)) != 0]
    result_dict = construct_statistic_dict(result_lst)
    print result_dict
    result_dict = calculate_whole_tree(result_dict["kernel function execution"])
    draw_statistic_circle_graph(result_dict)
    # draw_statistic_bar_graph(result_dict)
    return result_dict


def count_tree_path(target_dict, result_dict, previous_key):
    if type(target_dict) != type(dict()):
        return None
    for key in target_dict:
        current_item = target_dict[key]
        current_key = '::'.join([item for item in [previous_key, key] if len(item) != 0])
        if type(current_item) == type(dict()):
            count_tree_path(current_item, result_dict, current_key)
        else:
            if current_key not in result_dict:
                result_dict[current_key] = target_dict[key]
            else:
                result_dict[current_key] += target_dict[key]


def analysis_log_files(file_names):
    content = ""
    for file_name in file_names:
        content += open(file_name, 'r').read() + "\n\n"
    result_lst = parse_item(content)
    result_lst = [parse_bug_type(bug_item)[0] for bug_item in result_lst if len(parse_bug_type(bug_item)) != 0]
    result_dict = construct_statistic_dict(result_lst)
    # print result_dict
    whole_result_dict = calculate_whole_tree(result_dict)  # count bug distribution
    print whole_result_dict
    real_result_dict = count_tree_leaf(result_dict["kernel function execution"])  # count bug root cause
    # print real_result_dict
    # print real_result_dict, sum([real_result_dict[key] for key in real_result_dict])
    new_result_dict = dict()
    count_tree_path(result_dict["kernel function execution"], new_result_dict, "")  # count bug type symptoms/root cause pair
    # count_tree_path(result_dict, new_result_dict, "")
    print new_result_dict
    # draw_statistic_circle_graph(result_dict)
    # draw_statistic_bar_graph(result_dict)
    return result_dict


def parse_specify_bug(file_names, target_file):
    content = ""
    for file_name in file_names:
        content += open(file_name, 'r').read() + "\n\n"
    result_lst = parse_item(content)
    result_lst = [item for item in result_lst if item.find("Test case sometimes failed::synchronization") != -1]
    f = open(target_file, 'w')
    f.write("\n".join(result_lst))
    f.close()


def transform_to_pure_hours(time_tuple):
    return time_tuple[0] * 24 + time_tuple[1]


def transform_to_day_hours(hours):
    return hours / 24, hours % 24


def parse_all_sync_bug(target_file, report_file):
    f = open(target_file, 'r')
    content = f.read()
    f.close()
    result_lst = parse_item(content)
    result = [["commit message", "Time effort", "Version iterator effort"]]
    time_lst = list()
    version_lst = list()
    for item in result_lst:
        current_row = parse_bug_effort(item)
        time_lst.append(current_row[1])
        version_lst.append(int(current_row[2]))
        current_row[1] = str(current_row[1][0]) + " days, " + str(current_row[1][1]) + " hrs"
        current_row = [str(single_item) for single_item in current_row]
        result.append(current_row)
    result = [','.join(row) for row in result]
    print "avg of version iter: " + str(sum(version_lst) / len(version_lst))
    print "max of version iter: " + str(max(version_lst))
    print "min of version iter: " + str(min(version_lst))
    pure_hours = [transform_to_pure_hours(item) for item in time_lst]
    print "avg of time effort: " + str(transform_to_day_hours(sum(pure_hours) / len(pure_hours)))
    print "max of time effort: " + str(transform_to_day_hours(max(pure_hours)))
    print "min of time effort: " + str(transform_to_day_hours(min(pure_hours)))
    with open(report_file, 'w') as f:
        f.write('\n'.join(result))


def parse_all_synchronization_bug(file_names):
    content = ""
    for file_name in file_names:
        content += open(file_name, 'r').read() + "\n\n"
    result_lst = parse_item(content)
    result_lst = [item for item in result_lst if item.find("::synchronization") != -1 and item.find("kernel function execution::") != -1]
    result_dict = dict()
    for item in result_lst:
        current_item = parse_bug_type(item)[0]
        current_symptom = current_item.split("::")[1]
        if current_symptom == "lower time performance":
            print item
        if current_symptom not in result_dict:
            result_dict[current_symptom] = 0
        result_dict[current_symptom] += 1
    return result_dict


def draw_statistic_circle_graph(target_dict):
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            return '{v:d} ({p:.2f}%)'.format(p=pct,v=val)
        return my_autopct
    labels = [key for key in target_dict]
    total_sum = sum([target_dict[key] for key in target_dict])
    sizes = [float(target_dict[key]) / total_sum * 100 for key in target_dict]
    values = [target_dict[key] for key in target_dict]
    print sizes
    plt.figure(figsize=(6, 9))
    patches, l_text, p_text = plt.pie(sizes, labels=labels,
                                labeldistance=1.1, autopct=make_autopct(values), shadow=False,
                                startangle=90, pctdistance=0.6)
    for t in l_text:
        t.set_size(0)
    for t in p_text:
        t.set_size(15)
    plt.legend(loc='lower right', #bbox_to_anchor=(6, 0),
           bbox_transform=plt.gcf().transFigure, fontsize=14)
    plt.axis('equal')
    plt.show()


def draw_statistic_bar_graph(target_dict):
    labels = [key for key in target_dict]
    num_lst = [target_dict[key] for key in target_dict]
    plt.bar(range(len(num_lst)), num_lst, tick_label=labels)
    plt.show()


if __name__ == '__main__':
    # result = analysis_log_file("./report_arrayfire_current_real.log")
    # result = analysis_log_file("./report_current_kaldi_real.log")
    # result = analysis_log_files(["./raw_data_report_script/report_mshadow_current_real.log", "./raw_data_report_script/report_arrayfire_current_real.log",
    #                              "./raw_data_report_script/report_current_kaldi_real.log", "./raw_data_report_script/report_thundersvm_current_real.log",
    #                              "./raw_data_report_script/report_cuda-convnet2.log"])
    # parse_specify_bug(["./new_log/report_mshadow_current_real.log", "./new_log/report_arrayfire_current_real.log",
    #                              "./new_log/report_current_kaldi_real.log", "./new_log/report_thundersvm_current_real.log",
    #                              "./new_log/report_cuda-convnet2.log"], "./AAAAA.log")
    # parse_all_sync_bug("./All sync bugs.log", "./sync_report.csv")
    draw_statistic_circle_graph({
        "host resource retrieve ": 34,
        "host resource preparation": 68,
        "kernel function execution": 217,
    })
    # result = parse_all_synchronization_bug(["./new_log/report_mshadow_current_real.log", "./new_log/report_arrayfire_current_real.log",
    #                              "./new_log/report_current_kaldi_real.log", "./new_log/report_thundersvm_current_real.log",
    #                              "./new_log/report_cuda-convnet2.log"])
    print result
