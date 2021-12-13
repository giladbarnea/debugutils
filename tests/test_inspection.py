from debugutils.inspection import _get_argnames
class TestVarInfo:
    def test_get_argnames(self):
        context = "print(topic_name, partition_key, title='ConfluentKafkaTool.send_bytes_message(topic_name, partition_key, data_bytes)')"
        argnames = _get_argnames(context)
        assert argnames == ['topic_name', 'partition_key', 'title']