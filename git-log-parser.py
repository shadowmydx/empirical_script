# TODO: parse commit message and commit id and its previous brother according the filter condition
# TODO: parse diff between target commit and its brother by given condition
import os
import subprocess
import re
from search import search_content
from search import search_string_by_line
from search import search_regex_by_line


class CommitMessage(object):
    def __init__(self, item_lst):
        self.commit_id = re.split("\s+", item_lst[0])[1]
        self.author = item_lst[1][8:].strip()
        self.date = item_lst[2][5:].strip()
        self.commit_message = ''.join(item_lst[3:]).strip()
        self.commit_message = '\n'.join(re.split("\s\s\s+", self.commit_message))


def execute_os_cmd(target_cmd, working_directory='.'):
    os.chdir(working_directory)
    args_lst = re.split("\s+", target_cmd)
    return subprocess.check_output(args_lst)


def execute_init_for_diff(git_repo):
    os.chdir(git_repo)
    target_cmd = r'git config diff.renameLimit 3000'
    return execute_os_cmd(target_cmd)


def get_git_log_by_given_directory(target_directory):
    cmd_pattern = "git log"
    return execute_os_cmd(cmd_pattern, target_directory)


def split_git_log_to_item(log_content_lst):
    result = list()
    tmp_item = list()
    for single_line in log_content_lst:
        if single_line[0: 6] == "commit":
            if len(tmp_item) != 0:
                result.append(CommitMessage(tmp_item))
                tmp_item = list()
            tmp_item.append(single_line)
        else:
            tmp_item.append(single_line)
    return result


def get_diff_message_between_commit(commit_id, parent_id):
    cmd_pattern = "git diff  [id1]  [id2]"
    real_cmd = cmd_pattern.replace("[id1]", commit_id)
    real_cmd = real_cmd.replace("[id2]", parent_id)
    return execute_os_cmd(real_cmd)


def get_diff_message_by_hash(commit_tuple):
    commit_hash = commit_tuple.commit_id
    cmd_pattern = r'git cat-file -p [id]'
    real_cmd = cmd_pattern.replace('[id]', commit_hash)
    parent_msg = execute_os_cmd(real_cmd)
    parent_id = parent_msg.split('\n')[1].split(' ')[1]
    return get_diff_message_between_commit(commit_hash, parent_id)


def show_result_from_diff_lst(diff_lst, report_file, write_diff=True):
    if len(diff_lst) == 0:
        print 'no content parsed.'
        return
    with open(report_file, 'w') as f:
        for single_diff_item in diff_lst:
            f.write("===============================================================\n")
            f.write("commit comment:   " + single_diff_item[1].commit_message + "\n")
            if write_diff:
                f.write("\n" + single_diff_item[0] + '\n')
            f.write("===============================================================\n\n")


def generate_file_list(target_lst):
    result = list()
    for single_file in target_lst:
        result.append(single_file.split("\\")[-1])
    return result


def check_combine(target_lst):
    def _checker(diff_message):
        for content in target_lst:
            if diff_message.find(content) != -1:
                return True
        return False
    return _checker


def main(git_repo, diff_message_parser, commit_message_parser, show_diff=False):
    log_content = get_git_log_by_given_directory(git_repo)
    message_lst = split_git_log_to_item(log_content.split('\n'))
    message_lst = [message_lst[index] for index in range(len(message_lst))
                   if commit_message_parser(message_lst[index])]
    diff_message = [(get_diff_message_by_hash(item), item) for item in message_lst]
    diff_message = [item for item in diff_message if diff_message_parser(item[0])]
    show_result_from_diff_lst(diff_message, "d:/important/report_" + git_repo.split('\\')[-1] + ".log", show_diff)


def track_file_history(file_lst, processor_fac):
    result_dict = dict()
    for single_file in file_lst:
        processor = processor_fac()
        target_folder, file_name = os.path.split(single_file)
        file_log_content = execute_os_cmd("git log " + file_name, target_folder)
        file_message_lst = split_git_log_to_item(file_log_content.split('\n'))
        for single_message in file_message_lst:
            processor['processor'](single_message)
        result_dict[single_file] = processor['get_result']()
    return result_dict


def processor_factory():
    content_dict = dict()
    result_lst = list()

    def _processor(single_message):
        if single_message.commit_message.lower().find('mem') != -1:
            diff_message = get_diff_message_by_hash(single_message)
            # if diff_message.find("__syncthreads") != -1:
            #     result_lst.append((diff_message, single_message))

            result_lst.append((diff_message, single_message))

    def _get_result_lst():
        return result_lst

    content_dict['get_result'] = _get_result_lst
    content_dict['processor'] = _processor
    return content_dict


def track_all_file_suspect(git_repo, processor_fac, show_diff=False):
    root_folder = 'd:/important/' + git_repo.split('\\')[-1]
    if not os.path.exists(root_folder):
        os.mkdir(root_folder)
    execute_init_for_diff(git_repo)
    suspect_file_lst = search_content(git_repo, search_regex_by_line("__(\w+)__"))
    print suspect_file_lst
    all_files = track_file_history(suspect_file_lst, processor_fac)
    for single_file in all_files:
        show_lst = all_files[single_file]
        folder, file_name = os.path.split(single_file)
        show_result_from_diff_lst(show_lst, root_folder + "/" + file_name + ".log", show_diff)


def judge_if_cuda_code(target_content):
    target_lst = [len(re.findall("cuda[\w|\s]*?[(]", target_content)) != 0, target_content.find('__global__') != -1,
                  target_content.find('__device__') != -1, len(re.findall("[^<]<<<[^<]", target_content)) != 0]
    return len([item for item in target_lst if item]) != 0


if __name__ == '__main__':
    target_repo = r'D:\git-project\cuda-convnet2'
    # track_all_file_suspect(target_repo, processor_factory)
    target_file_lst = search_content(target_repo, search_string_by_line("__global__"))
    target_file_lst = generate_file_list(target_file_lst)
    target_file_lst = ['__sync']
    key_lst = ['error', 'fix', 'mem']

    main(target_repo,
         judge_if_cuda_code,
         lambda x: sum([1 for item in key_lst if x.commit_message.lower().find(item) == -1]) != len(key_lst),
         show_diff=False)
    # main(target_repo, check_combine(target_file_lst),
    #      lambda x: x.commit_message.lower().find('mem') != -1, show_diff=False)
    # main(target_repo, check_combine(target_file_lst),
    #      lambda x: x.commit_message.lower().find('mem') != -1 or x.commit_message.find("sync") != -1)

    # print get_git_log_by_given_directory(r"D:\git-project\CudaMiner")
    # print execute_os_cmd("git diff  a9a2972bfb94eeff49d0f0a9b1bd4b2666a93ebc  289eb72fe0da2c4e0534095369f39e4b4b01ac8b", r"D:\git-project\CudaMiner")
