import os


class bids_reader:
    def __init__(self, bids_dir):
        self.bids_dir = bids_dir

    def get_subject_list(self):
        """
        Return a list of subjects in the bids folder
        """

        subject_list = [i for i in os.listdir(self.bids_dir) if i[:4] == "sub-"]
        subject_list.sort()

        return subject_list

    def get_session_list(self, subj_id):
        """
        Return a list of sessions in the bids/{subj_id} folder
        """

        if subj_id[:4] != "sub-":
            subj_id = f"sub-{subj_id}"
        subj_dir = f"{self.bids_dir}/{subj_id}"
        assert os.path.isdir(subj_dir), f"Directory [{subj_dir}] does not exist."

        session_list = [i for i in os.listdir(f"{subj_dir}")]
        session_list.sort()

        return session_list

    def get_bold_list(
        self,
        subj_id,
        sess_id,
        ignore_tasks=[],
        ignore_phase=True,
        specific_task=None,
        full_path_flag=False,
        suffix="bold.nii.gz",
    ):
        """
        Returns a list of the bold runs in the bids/{subj_id}/{sess_id}/func folder
        """

        # add 'task-' in front of elements in `ignore_tasks`
        ignore_tasks = [f"task-{i}" if "task-" != i[:5] else i for i in ignore_tasks]

        if subj_id[:4] != "sub-":
            subj_id = f"sub-{subj_id}"
        if sess_id[:4] != "ses-":
            sess_id = f"ses-{sess_id}"
        sess_dir = f"{self.bids_dir}/{subj_id}/{sess_id}"
        func_dir = f"{sess_dir}/func"
        for _dir in [sess_dir, func_dir]:
            assert os.path.isdir(f"{_dir}"), f"Directory [{_dir}] does not exist."

        func_list = []
        # If `specific_task` is set, ONLY grab the labelled task name
        if specific_task is not None:
            for i in os.listdir(func_dir):
                if "task-" not in i:
                    continue
                task_name = f"task-{i.split('task-')[1].split('_')[0]}"
                if i[-len(suffix) :] == suffix and task_name in f"task-{specific_task}":
                    func_list.append(i)
        # Else: include all tasks that are not included in `ignore_tasks`
        else:
            for i in os.listdir(func_dir):
                if "task-" not in i:
                    continue
                task_name = f"task-{i.split('task-')[1].split('_')[0]}"
                if i[-len(suffix) :] == suffix and task_name not in ignore_tasks:
                    func_list.append(i)

        func_list.sort()

        if ignore_phase:
            func_list = [bold for bold in func_list if "part-phase" not in bold]

        self._check_str_in_list(func_list, "_dir-")

        if full_path_flag:
            return [f"{func_dir}/{i}" for i in func_list]
        else:
            return func_list

    def get_t1w_list(self, subj_id):
        t1w_list = []
        if subj_id[:4] != "sub-":
            subj_id = f"sub-{subj_id}"
        for sess_id in self.get_session_list(subj_id):
            anat_dir = f"{self.bids_dir}/{subj_id}/{sess_id}/anat"
            if os.path.isdir(anat_dir):
                # Check T1w suffix
                dup_list = []
                for i in os.listdir(anat_dir):
                    _subj_id = i.split("sub-")[1].split("_")[0]
                    _sess_id = i.split("ses-")[1].split("_")[0]
                    if "acq-" in i and "run-" in i:
                        acq = i.split("acq-")[1].split("_")[0]
                        run = i.split("run-")[1].split("_")[0]
                        if f"{acq}_{run}" in dup_list:
                            continue
                        else:
                            dup_list.append(f"{acq}_{run}")
                            if acq == "MP2RAGE":
                                t1w_list.append(
                                    {
                                        "MP2RAGE": {
                                            "UNI": f"{anat_dir}/sub-{_subj_id}_ses-{_sess_id}_acq-UNI_run-{run}_MP2RAGE.nii.gz",
                                            "INV1": f"{anat_dir}/sub-{_subj_id}_ses-{_sess_id}_inv-1_run-{run}_part-mag_MP2RAGE.nii.gz",
                                            "INV2": f"{anat_dir}/sub-{_subj_id}_ses-{_sess_id}_inv-2_run-{run}_part-mag_MP2RAGE.nii.gz",
                                        }
                                    }
                                )
                            elif acq == "MPRAGE":
                                t1w_list.append(
                                    {
                                        "MPRAGE": {
                                            "T1w": f"{anat_dir}/sub-{_subj_id}_ses-{_sess_id}_acq-MPRAGE_run-{run}_T1w.nii.gz"
                                        }
                                    }
                                )
                            else:
                                NotImplemented

        # Assert all paths exist
        for _dict in t1w_list:
            for value in _dict.values():
                for _type, path in value.items():
                    assert os.path.exists(path), f"Path [{path}] does not exist."

        if len(t1w_list) > 1:
            print("WARNING: multiple T1w acquisitions were found.")
            for _t1w in t1w_list:
                print(_t1w)

        assert len(t1w_list) != 0, "No T1w acquisitions were found."

        return t1w_list[-1]

    def _check_str_in_list(self, str_list, _str):
        for s in str_list:
            assert _str in s, f"{s} does not contain {_str}."
