# test export, buildmap

# def test_add_family(self):
#         pass  # TODO

    # test missing root file, multiple exports, different ids TODO
    # def test_FamDB_file_check(self):
    #     with self.assertRaises(SystemExit):
    #         other_file = tempfile.NamedTemporaryFile(
    #             dir="/tmp", prefix="bad", suffix=".0.h5"
    #         )
    #         famdb = TestDatabase.famdb
    #         other_file.close()

    # def test_FamDB_id_check(self):
    #     with self.assertRaises(SystemExit):
    #         new_info = copy.deepcopy(FILE_INFO)
    #         new_info['meta']['id'] = 'uuidNN'
    #         with FamDBRoot(TestDatabase.filenames[1], "r+") as db:
    #             db.set_file_info(new_info)
    #         famdb = FamDB('/tmp')
    #         with FamDBRoot(TestDatabase.filenames[1], "r+") as db:
    #             db.set_file_info(FILE_INFO)
