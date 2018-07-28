from django.db import models

# Create your models here.

class MysqlDb(models.Model):
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    tags = models.CharField(max_length=255)
    version = models.CharField(max_length=255, blank=True, null=True)
    uptime = models.IntegerField(blank=True, null=True)
    max_connections = models.CharField(max_length=255, blank=True, null=True)
    threads_connected = models.IntegerField(blank=True, null=True)
    threads_running = models.IntegerField(blank=True, null=True)
    threads_created = models.IntegerField(blank=True, null=True)
    threads_cached = models.IntegerField(blank=True, null=True)
    threads_waited = models.IntegerField(blank=True, null=True)
    conn_rate = models.CharField(max_length=255, blank=True, null=True)
    conn_rate_level = models.CharField(max_length=255, blank=True, null=True)
    qps = models.IntegerField(db_column='QPS', blank=True, null=True)  # Field name made lowercase.
    tps = models.IntegerField(db_column='TPS', blank=True, null=True)  # Field name made lowercase.
    bytes_received = models.IntegerField(blank=True, null=True)
    bytes_send = models.IntegerField(blank=True, null=True)
    mon_status = models.CharField(max_length=255)
    rate_level = models.CharField(max_length=255)
    chk_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mysql_db'


class MysqlDbHis(models.Model):
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    tags = models.CharField(max_length=255)
    version = models.CharField(max_length=255, blank=True, null=True)
    uptime = models.IntegerField(blank=True, null=True)
    max_connections = models.CharField(max_length=255, blank=True, null=True)
    threads_connected = models.IntegerField(blank=True, null=True)
    threads_running = models.IntegerField(blank=True, null=True)
    threads_created = models.IntegerField(blank=True, null=True)
    threads_cached = models.IntegerField(blank=True, null=True)
    threads_waited = models.IntegerField(blank=True, null=True)
    conn_rate = models.CharField(max_length=255, blank=True, null=True)
    conn_rate_level = models.CharField(max_length=255, blank=True, null=True)
    qps = models.IntegerField(db_column='QPS', blank=True, null=True)  # Field name made lowercase.
    tps = models.IntegerField(db_column='TPS', blank=True, null=True)  # Field name made lowercase.
    bytes_received = models.IntegerField(blank=True, null=True)
    bytes_send = models.IntegerField(blank=True, null=True)
    mon_status = models.CharField(max_length=255)
    rate_level = models.CharField(max_length=255)
    chk_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'mysql_db_his'


class MysqlDbRate(models.Model):
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    tags = models.CharField(max_length=255)
    conn_decute = models.IntegerField()
    cpu_decute = models.IntegerField()
    mem_decute = models.IntegerField()
    disk_decute = models.IntegerField()
    db_rate = models.IntegerField()
    db_rate_level = models.CharField(max_length=255)
    db_rate_color = models.CharField(max_length=255)
    db_rate_reason = models.CharField(max_length=255)
    rate_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'mysql_db_rate'


class MysqlDbRateHis(models.Model):
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    tags = models.CharField(max_length=255)
    conn_decute = models.IntegerField()
    cpu_decute = models.IntegerField()
    mem_decute = models.IntegerField()
    disk_decute = models.IntegerField()
    db_rate = models.IntegerField()
    db_rate_level = models.CharField(max_length=255)
    db_rate_color = models.CharField(max_length=255)
    db_rate_reason = models.CharField(max_length=255)
    rate_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'mysql_db_rate_his'


class MysqlRepl(models.Model):
    tags = models.CharField(max_length=255)
    server_id = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    is_master = models.CharField(max_length=255, blank=True, null=True)
    is_slave = models.CharField(max_length=255, blank=True, null=True)
    mysql_role = models.CharField(max_length=255, blank=True, null=True)
    read_only = models.CharField(max_length=255, blank=True, null=True)
    master_server = models.CharField(max_length=255, blank=True, null=True)
    master_port = models.CharField(max_length=255, blank=True, null=True)
    slave_io_run = models.CharField(max_length=255, blank=True, null=True)
    slave_io_rate = models.CharField(max_length=255, blank=True, null=True)
    slave_sql_run = models.CharField(max_length=255, blank=True, null=True)
    slave_sql_rate = models.CharField(max_length=255, blank=True, null=True)
    delay = models.CharField(max_length=255, blank=True, null=True)
    delay_rate = models.CharField(max_length=255, blank=True, null=True)
    current_binlog_file = models.CharField(max_length=255, blank=True, null=True)
    current_binlog_pos = models.CharField(max_length=255, blank=True, null=True)
    master_binlog_file = models.CharField(max_length=255, blank=True, null=True)
    master_binlog_pos = models.CharField(max_length=255, blank=True, null=True)
    master_binlog_space = models.CharField(max_length=255, blank=True, null=True)
    chk_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mysql_repl'


class MysqlReplHis(models.Model):
    tags = models.CharField(max_length=255)
    server_id = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    is_master = models.CharField(max_length=255, blank=True, null=True)
    is_slave = models.CharField(max_length=255, blank=True, null=True)
    mysql_role = models.CharField(max_length=255, blank=True, null=True)
    read_only = models.CharField(max_length=255, blank=True, null=True)
    master_server = models.CharField(max_length=255, blank=True, null=True)
    master_port = models.CharField(max_length=255, blank=True, null=True)
    slave_io_run = models.CharField(max_length=255, blank=True, null=True)
    slave_io_rate = models.CharField(max_length=255, blank=True, null=True)
    slave_sql_run = models.CharField(max_length=255, blank=True, null=True)
    slave_sql_rate = models.CharField(max_length=255, blank=True, null=True)
    delay = models.CharField(max_length=255, blank=True, null=True)
    delay_rate = models.CharField(max_length=255, blank=True, null=True)
    current_binlog_file = models.CharField(max_length=255, blank=True, null=True)
    current_binlog_pos = models.CharField(max_length=255, blank=True, null=True)
    master_binlog_file = models.CharField(max_length=255, blank=True, null=True)
    master_binlog_pos = models.CharField(max_length=255, blank=True, null=True)
    master_binlog_space = models.CharField(max_length=255, blank=True, null=True)
    chk_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mysql_repl_his'

class TabMysqlServers(models.Model):
    tags = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    port = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    user_os = models.CharField(max_length=255)
    password_os = models.CharField(max_length=255)
    connect = models.CharField(max_length=255, blank=True, null=True)
    connect_cn = models.CharField(max_length=255, blank=True, null=True)
    repl = models.CharField(max_length=255, blank=True, null=True)
    repl_cn = models.CharField(max_length=255, blank=True, null=True)
    conn = models.CharField(max_length=255, blank=True, null=True)
    conn_cn = models.CharField(max_length=255, blank=True, null=True)
    err_info = models.CharField(max_length=255, blank=True, null=True)
    err_info_cn = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tab_mysql_servers'