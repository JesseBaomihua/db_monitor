#! /usr/bin/python
# encoding:utf-8

import base64
import sys
import time
from multiprocessing import Process;

import MySQLdb
import cx_Oracle

import check_mysql as check_msql
import check_oracle as check_ora
import check_os as check_os
import tools as tools
import alarm as alarm
import my_log as my_log

reload(sys)
sys.setdefaultencoding('utf-8')
# 配置文件
import ConfigParser
conf = ConfigParser.ConfigParser()
conf.read('config/db_monitor.conf')

def check_linux(tags,host,host_name,user,password):
    # 密钥解密
    password = base64.decodestring(password)
    my_log.logger.info('%s：开始获取系统监控信息' % tags)
    try:
        my_log.logger.info('%s：初始化os_info表' % tags)
        insert_sql = "insert into os_info_his select * from os_info where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from os_info where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        # 发送网络流量，接收网络流量，cpu使用率
        recv_kbps,send_kbps,cpu_used = check_os.os_get_info(host, user, password)
        # cpu使用率评级
        cpu_rate_level = tools.get_rate_level(float(cpu_used))
        mem_used = check_os.os_get_mem(host, user, password)
        # 内存使用率评级
        mem_rate_level = tools.get_rate_level(float(mem_used))
        # 主机状态评级
        os_rate_level = 'green'
        insert_os_used_sql = 'insert into os_info(tags,host,host_name,recv_kbps,send_kbps,cpu_used,cpu_rate_level,mem_used,mem_rate_level,mon_status,rate_level) value(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
        value = (tags,host, host_name, recv_kbps,send_kbps,cpu_used,cpu_rate_level, mem_used,mem_rate_level, 'connected',os_rate_level)

        my_log.logger.info('%s：获取系统监控数据(CPU：%s MEM：%s)' % (tags, cpu_used, mem_used))
        # print insert_cpu_used_sql
        tools.mysql_exec(insert_os_used_sql, value)

        my_log.logger.info('%s：开始获取文件系统监控信息' % tags)
        my_log.logger.info('%s：初始化os_filesystem表' % tags)
        insert_sql = "insert into os_filesystem_his select * from os_filesystem where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from os_filesystem where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        file_sys = check_os.os_get_disk(host, user, password)
        for i in xrange(len(file_sys)):
            disk_rate = float(file_sys[i]['used'].replace('%', ''))
            disk_rate_level = tools.get_rate_level(float(file_sys[i]['used'].replace('%', '')))
            insert_file_sys_sql = "insert into os_filesystem(tags,host,host_name,filesystem_name,size,avail,pct_used,disk_rate_level) values(%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (
                tags,host, host_name, file_sys[i]['name'], file_sys[i]['size'], file_sys[i]['avail'],
                file_sys[i]['used'].replace('%', ''),disk_rate_level)
            my_log.logger.info('%s：获取文件系统使用率(路径名：%s 使用率：%s)' % (tags, file_sys[i]['name'], file_sys[i]['used']))
            tools.mysql_exec(insert_file_sys_sql, value)

        # 更新主机评分信息
        my_log.logger.info('%s :开始更新Linux主机评分信息' % tags)
        delete_sql = "delete from linux_rate where tags= '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        # 内存使用率扣分
        linux_mem_decute_reason = ''
        mem_stat = tools.mysql_query(
            "select host,host_name,mem_used from os_info where mem_used is not null and host = '%s'" % host)
        if mem_stat == 0:
            my_log.logger.warning('%s：内存使用率未采集到数据' % host)
            linux_mem_decute = 0
        else:
            linux_mem_used = float(mem_stat[0][2])
            linux_mem_decute = tools.get_decute(linux_mem_used)
            if linux_mem_decute <> 0:
                linux_mem_decute_reason = '内存使用率：%d%% \n' % linux_mem_used
            else:
                linux_mem_decute_reason = ''

        # cpu使用率扣分
        linux_cpu_decute_reason = ''
        cpu_stat = tools.mysql_query(
            "select host,host_name,cpu_used from os_info where cpu_used is not null and host = '%s'" % host)
        if cpu_stat == 0:
            my_log.logger.warning('%s：CPU使用率未采集到数据' % host)
            linux_cpu_decute = 0
        else:
            linux_cpu_used = float(cpu_stat[0][2])
            linux_cpu_decute = tools.get_decute(linux_cpu_used)
            if linux_cpu_decute <> 0:
                linux_cpu_decute_reason = 'CPU使用率：%d%% \n' % linux_cpu_used
            else:
                linux_cpu_decute_reason = ''

        linux_top_decute = max(linux_cpu_decute, linux_mem_decute)
        linux_all_rate = 100 - linux_top_decute
        if linux_all_rate >= 60:
            linux_rate_color = 'green'
            linux_rate_level = 'success'
        elif linux_all_rate >= 20 and linux_all_rate < 60:
            linux_rate_color = 'yellow'
            linux_rate_level = 'warning'
        else:
            linux_rate_color = 'red'
            linux_rate_level = 'danger'
        linux_all_decute_reason =   linux_cpu_decute_reason + linux_mem_decute_reason

        # 插入总评分及扣分明细
        insert_sql = "insert into linux_rate(host,tags,cpu_decute,mem_decute,linux_rate,linux_rate_level,linux_rate_color,linux_rate_reason) select host,tags,'%s','%s','%s','%s','%s','%s' from tab_linux_servers where tags ='%s'" % (
             linux_cpu_decute, linux_mem_decute, linux_all_rate, linux_rate_level, linux_rate_color,
            linux_all_decute_reason, tags)
        tools.mysql_exec(insert_sql, '')
        my_log.logger.info('%s扣分明细，cpu使用率扣分:%s，内存使用率扣分:%s，总评分:%s,扣分原因:%s' %(tags,linux_cpu_decute,linux_mem_decute,linux_all_rate,linux_all_decute_reason))



    except Exception, e:
        error_msg = "%s 目标主机连接失败：%s" % (tags, str(e))
        os_rate_level = 'red'
        my_log.logger.error(error_msg)
        insert_sql = "insert into os_info_his select * from os_info where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from os_info where tags='%s'" % tags
        tools.mysql_exec(delete_sql, '')
        error_sql = "insert into os_info(tags,host,host_name,mon_status,rate_level) values(%s,%s,%s,%s,%s)"
        value = (tags,host, host_name, 'connected error',os_rate_level)
        tools.mysql_exec(error_sql, value)
        # 更新linux主机打分信息
        my_log.logger.info('%s :开始更新linux主机评分信息' %tags)
        delete_sql = "delete from linux_rate where tags= '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        insert_sql = "insert into linux_rate(host,tags,linux_rate,linux_rate_level,linux_rate_color,linux_rate_reason) select host,tags,'0','danger','red','connected error' from tab_linux_servers where tags ='%s'" % tags
        tools.mysql_exec(insert_sql, '')
        my_log.logger.info('%s扣分明细，总评分:%s,扣分原因:%s' % (tags,'0', 'connected error'))




def check_oracle(tags,host,port,service_name,user,password,user_os,password_os):
    my_log.logger.info('%s等待2秒待linux主机信息采集完毕' %tags)
    time.sleep(2)
    password = base64.decodestring(password)
    password_os = base64.decodestring(password_os)
    url = host + ':' + port + '/' + service_name
    # 转移监控当前表数据到历史表
    # tools.mysql_exec('insert into oracle_db_his select * from oracle_db', '')
    # tools.mysql_exec('insert into oracle_tbs_his select * from oracle_tbs', '')
    # tools.mysql_exec('insert into oracle_tmp_tbs_his select * from oracle_tmp_tbs', '')
    # tools.mysql_exec('insert into oracle_undo_tbs_his select * from oracle_undo_tbs', '')
    # tools.mysql_exec('insert into os_info_his select * from os_info', '')
    # tools.mysql_exec('insert into os_filesystem_his select * from os_filesystem', '')

    # tools.mysql_exec('delete from oracle_db', '')
    # tools.mysql_exec('delete from oracle_tbs', '')
    # tools.mysql_exec('delete from oracle_tmp_tbs', '')
    # tools.mysql_exec('delete from oracle_undo_tbs', '')
    # tools.mysql_exec('delete from os_info', '')
    # tools.mysql_exec('delete from os_filesystem', '')
    try:
        conn = cx_Oracle.connect(user, password, url)

        # 表空间监控
        my_log.logger.info('%s：开始获取Oracle数据库表空间监控信息' % tags)

        my_log.logger.info('%s：初始化oracle_tbs表' % tags)
        insert_sql = "insert into oracle_tbs_his select * from oracle_tbs where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_tbs where tags = '%s' " % tags
        tools.mysql_exec(delete_sql, '')

        tbs = check_ora.check_tbs(conn)
        for line in tbs:
            if not line[6]:
                line[6] = 0
            tbs_percent = float(line[6])
            tbs_rate_level = tools.get_rate_level(tbs_percent)
            insert_tbs_sql = "insert into oracle_tbs(tags,host,port,service_name,tbs_name,datafile_count,size_gb,free_gb,used_gb,max_free,pct_used,pct_free,rate_level) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (
                tags, host, port, service_name, line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7],
                tbs_rate_level)

            my_log.logger.info('%s：获取Oracle数据库表空间使用率(表空间名：%s 使用率：%s)' % (tags, line[0], line[6]))

            tools.mysql_exec(insert_tbs_sql, value)
        # db信息监控
        my_log.logger.info('%s：开始获取Oracle数据库监控信息' % tags)

        my_log.logger.info('%s：初始化oracle_db表' % tags)
        insert_sql = "insert into oracle_db_his select * from oracle_db where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_db where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        dbnameinfo = check_ora.get_dbname_info(conn)
        instance_info = check_ora.get_instance_info(conn)
        process = check_ora.check_process(conn)
        asm = check_ora.check_asm(conn)
        archive_used = check_ora.get_archived(conn)
        if not archive_used:
            archive_used = [('None'),0]
            archive_rate_level = 'None'
        else:
            archive_rate_level = tools.get_rate_level(archive_used[0][0])
        adg_trs = check_ora.check_adg_trs(conn)
        adg_apl = check_ora.check_adg_apl(conn)
        err_info = check_ora.check_err(conn, host, user_os, password_os)
        db_rate_level = 'green'
        # 连接数评级
        conn_percent = float(process[0][3])
        conn_rate_level = tools.get_rate_level(conn_percent)
        # adg
        if len(adg_trs) > 0:
            # adg传输评级
            transport_value = float(adg_trs[0][1])
            if transport_value >= 60 * 5:
                transport_rate_level = 'red'
            elif transport_value > 0 and transport_value < 60 * 5:
                transport_rate_level = 'yellow'
            else:
                transport_rate_level = 'green'
            apply_value = float(adg_apl[0][1])
            if apply_value >= 60 * 5:
                apply_rate_level = 'red'
            elif apply_value > 0 and transport_value < 60 * 5:
                apply_rate_level = 'yellow'
            else:
                apply_rate_level = 'green'

            insert_db_sql = "insert into oracle_db(tags,host,port,service_name,dbname,db_unique_name,database_role,open_mode,log_mode,archive_used,archive_rate_level,inst_id,instance_name,host_name,max_process,current_process,percent_process,conn_rate_level,adg_transport_lag,adg_apply_lag,adg_transport_value,adg_transport_rate_level,adg_apply_value,adg_apply_rate_level,mon_status,err_info,rate_level) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (
                tags, host, port, service_name, dbnameinfo[0][0], dbnameinfo[0][1], dbnameinfo[0][2], dbnameinfo[0][3],dbnameinfo[0][4],archive_used[0][0],archive_rate_level,
                instance_info[0][0],
                instance_info[0][1],
                instance_info[0][2], process[0][2], process[0][1], process[0][3], conn_rate_level, adg_trs[0][0],
                adg_apl[0][0],
                adg_trs[0][1], transport_rate_level, adg_apl[0][1], apply_rate_level, 'connected', err_info,
                db_rate_level)
            tools.mysql_exec(insert_db_sql, value)
            my_log.logger.info('%s：获取Oracle数据库监控数据(数据库名：%s 数据库角色：%s 数据库状态：%s 连接数使用率：%s )' % (
                tags, dbnameinfo[0][0], dbnameinfo[0][2], dbnameinfo[0][3], process[0][3]))

        # not adg
        else:
            insert_db_sql = "insert into oracle_db(tags,host,port,service_name,dbname,db_unique_name,database_role,open_mode,log_mode,archive_used,archive_rate_level,inst_id,instance_name,host_name,max_process,current_process,percent_process,conn_rate_level,mon_status,err_info,rate_level) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (
                tags, host, port, service_name, dbnameinfo[0][0], dbnameinfo[0][1], dbnameinfo[0][2], dbnameinfo[0][3],dbnameinfo[0][4],archive_used[0][0],archive_rate_level,
                instance_info[0][0],
                instance_info[0][1],
                instance_info[0][2], process[0][2], process[0][1], process[0][3], conn_rate_level, 'connected',
                err_info,
                db_rate_level)
            tools.mysql_exec(insert_db_sql, value)
            my_log.logger.info('%s：获取Oracle数据库监控数据(数据库名：%s 数据库角色：%s 数据库状态：%s 连接数使用率：%s )' % (
                tags, dbnameinfo[0][0], dbnameinfo[0][2], dbnameinfo[0][3], process[0][3]))

        # 密码过期信息监控
        my_log.logger.info('%s：开始获取Oracle数据库用户密码过期信息' % tags)

        my_log.logger.info('%s：初始化oracle_expired_pwd表' % tags)
        delete_sql = "delete from oracle_expired_pwd where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        pwd_info = check_ora.get_pwd_info(conn)
        for line in pwd_info:
            insert_pwd_info_sql = "insert into oracle_expired_pwd(tags,host,port,service_name,username,result_number) values(%s,%s,%s,%s,%s,%s)"
            value = (tags, host, port, service_name, line[0], line[1])
            tools.mysql_exec(insert_pwd_info_sql, value)

        # 等待事件监控
        my_log.logger.info('%s：开始获取Oracle数据库等待事件信息' % tags)

        my_log.logger.info('%s：初始化oracle_db_event表' % tags)
        insert_sql = "insert into oracle_db_event_his select * from oracle_db_event where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_db_event where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        event_info = check_ora.get_event_info(conn)
        for line in event_info:
            insert_event_info_sql = "insert into oracle_db_event(tags,host,port,service_name,event_no,event_name,event_cnt) values(%s,%s,%s,%s,%s,%s,%s)"
            value = (tags, host, port, service_name, line[0], line[1], line[2])
            tools.mysql_exec(insert_event_info_sql, value)

        # 锁等待监控
        my_log.logger.info('%s：开始获取Oracle数据库锁等待信息' % tags)

        my_log.logger.info('%s：初始化oracle_Lock表' % tags)
        delete_sql = "delete from oracle_lock where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        lock_info = check_ora.get_lock_info(conn)
        for line in lock_info:
            insert_lock_info_sql = "insert into oracle_lock(tags,host,port,service_name,session,lmode,ctime,inst_id,lmode1,type) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (tags, host, port, service_name, line[0], line[1], line[2], line[3], line[6], line[8])
            tools.mysql_exec(insert_lock_info_sql, value)
            my_log.logger.info('%s 获取Oracle数据库锁等待信息' % tags)

        #  无效索引监控
        my_log.logger.info('%s：开始获取Oracle数据库无效索引信息' % tags)

        my_log.logger.info('%s：初始化oracle_invalid_index表' % tags)
        delete_sql = "delete from oracle_invalid_index where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        invalid_index_info = check_ora.get_invalid_index(conn)
        for line in invalid_index_info:
            insert_invalid_index_info_sql = "insert into oracle_invalid_index(tags,host,port,service_name,owner,index_name,partition_name,status) values(%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (tags, host, port, service_name, line[0], line[1], line[2], line[3])
            tools.mysql_exec(insert_invalid_index_info_sql, value)
            my_log.logger.info('%s 获取Oracle数据库无效索引信息' % tags)

        # 临时表空间监控
        my_log.logger.info('%s：开始获取Oracle数据库临时表空间监控信息' % tags)

        my_log.logger.info('%s：初始化oracle_tmp_tbs表' % tags)
        insert_sql = "insert into oracle_tmp_tbs_his select * from oracle_tmp_tbs where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_tmp_tbs where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        tmp_tbs = check_ora.check_tmp_tbs(conn)
        for line in tmp_tbs:
            tmp_pct_used = float(line[3])
            tmp_rate_level = tools.get_rate_level(tmp_pct_used)
            insert_tmp_tbs_sql = "insert into oracle_tmp_tbs(tags,host,port,service_name,tmp_tbs_name,total_mb,used_mb,pct_used,rate_level) values(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (tags, host, port, service_name, line[0], line[1], line[2], line[3], tmp_rate_level)
            tools.mysql_exec(insert_tmp_tbs_sql, value)
            my_log.logger.info('%s：获取Oracle数据库临时表空间使用率(temp表空间名：%s 使用率：%s)' % (tags, line[0], line[3]))

        # undo表空间监控
        my_log.logger.info('%s：开始获取Oracle数据库undo表空间监控信息' % tags)
        my_log.logger.info('%s：初始化oracle_undo_tbs表' % tags)
        insert_sql = "insert into oracle_undo_tbs_his select * from oracle_undo_tbs where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_undo_tbs where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        undo_tbs = check_ora.check_undo_tbs(conn)
        for line in undo_tbs:
            undo_pct_used = float(line[3])
            undo_rate_level = tools.get_rate_level(undo_pct_used)
            insert_undo_tbs_sql = "insert into oracle_undo_tbs(tags,host,port,service_name,undo_tbs_name,total_mb,used_mb,pct_used,rate_level) values(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            value = (tags, host, port, service_name, line[0], line[2], line[1], line[3], undo_rate_level)
            tools.mysql_exec(insert_undo_tbs_sql, value)
            my_log.logger.info('%s：获取Oracle数据库undo表空间使用率(undo表空间名：%s 使用率：%s)' % (tags, line[0], line[3]))

        # 更新数据库打分信息
        my_log.logger.info('%s :开始更新Oracle数据库评分信息' % tags)
        delete_sql = "delete from oracle_db_rate where tags= '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        # 内存使用率扣分
        mem_stat = tools.mysql_query(
            "select host,host_name,mem_used from os_info where mem_used is not null and host = '%s'" % host)
        if mem_stat == 0:
            my_log.logger.warning('%s：内存使用率未采集到数据' % tags)
            db_mem_decute = 0
            db_mem_decute_reason = ''
        else:
            db_mem_used = float(mem_stat[0][2])

            db_mem_decute = tools.get_decute(db_mem_used)
            if db_mem_decute <> 0:
                db_mem_decute_reason = '内存使用率：%d%% \n' % db_mem_used
            else:
                db_mem_decute_reason = ''

        # cpu使用率扣分
        cpu_stat = tools.mysql_query(
            "select host,host_name,cpu_used from os_info where cpu_used is not null and host = '%s'" % host)
        if cpu_stat == 0:
            my_log.logger.warning('%s：CPU使用率未采集到数据' % tags)
            db_cpu_decute = 0
            db_cpu_decute_reason = ''
        else:
            db_cpu_used = float(cpu_stat[0][2])
            db_cpu_decute = tools.get_decute(db_cpu_used)
            if db_cpu_decute <> 0:
                db_cpu_decute_reason = 'CPU使用率：%d%% \n' % db_cpu_used
            else:
                db_cpu_decute_reason = ''

        # 连接数扣分
        process_stat = tools.mysql_query(
            "select max_process,current_process,percent_process from oracle_db where current_process is not null and tags = '%s'" % tags)
        if process_stat == 0:
            my_log.logger.warning('%s：连接数未采集到数据' % tags)
            db_conn_decute = 0
            db_conn_decute_reason = ''
        else:
            db_conn_used = float(process_stat[0][2])
            db_conn_decute = tools.get_decute(db_conn_used)
            if db_conn_decute <> 0:
                db_conn_decute_reason = '连接数：%d%% \n' % db_conn_used
            else:
                db_conn_decute_reason = ''

        # 归档使用率扣分
        archive_stat = tools.mysql_query(
            "select archive_used from oracle_db where archive_used is not null and tags = '%s'" % tags)
        if archive_stat == 0:
            my_log.logger.warning('%s：归档未采集到数据' % tags)
            db_archive_decute = 0
            db_archive_decute_reason = ''
        else:
            db_archive_used = float(archive_stat[0][0])
            db_archive_decute = tools.get_decute(db_archive_used)
            if db_archive_decute <> 0:
                db_archive_decute_reason = '归档使用率：%d%% \n' % db_archive_used
            else:
                db_archive_decute_reason = ''

        # 综合性能扣分
        event_sql = ''' select tags, host, port, service_name, cnt_all from (select tags, host, port, service_name, sum(event_cnt) cnt_all
                                        from oracle_db_event_his where tags = '%s' and timestampdiff(minute, chk_time, current_timestamp()) < %s
                                        group by tags, host, port, service_name) t ''' %(tags,10)
        event_stat = tools.mysql_query(event_sql)
        if event_stat == 0:
            my_log.logger.warning('%s：归档未采集到数据' % tags)
            db_event_decute = 0
            db_event_decute_reason = ''
        else:
            db_event_cnt = float(event_stat[0][4])
            db_event_decute = db_event_cnt/10
            if db_event_decute <> 0:
                db_event_decute_reason = '等待时间数量：%d \n' % db_event_cnt
            else:
                db_event_decute_reason = ''

        # 表空间使用率扣分
        tbs_stat = tools.mysql_query(
            "select host,port,service_name,tbs_name,size_gb,free_gb,pct_used from oracle_tbs where tags='%s'" % tags)
        if tbs_stat == 0:
            my_log.logger.warning('%s：表空间使用率未采集到数据' % host)
            db_tbs_decute_reason = ''
            db_tbs_decute = 0
        else:
            db_tbs_decute_reason = ''
            db_tbs_decute = 0
            for each_tbs_stat in tbs_stat:
                each_tbs_name = each_tbs_stat[3]
                each_tbs_free = float(each_tbs_stat[5])
                each_tbs_used = float(each_tbs_stat[6])
                db_each_tbs_decute = tools.get_decute_tbs(each_tbs_used, each_tbs_free)
                if db_each_tbs_decute <> 0:
                    db_each_tbs_decute_reason = '%s表空间使用率：%d%% 剩余空间：%d \n' % (
                    each_tbs_name, each_tbs_used, each_tbs_free)
                else:
                    db_each_tbs_decute_reason = ''
                db_tbs_decute = max(db_tbs_decute, db_each_tbs_decute)
                db_tbs_decute_reason = db_tbs_decute_reason + db_each_tbs_decute_reason

        # 临时表空间使用率扣分
        tmp_tbs_stat = tools.mysql_query(
            "select host,port,service_name,tmp_tbs_name,total_mb,used_mb,pct_used from oracle_tmp_tbs where tags='%s'" % tags)
        if tmp_tbs_stat == 0:
            my_log.logger.warning('%s：临时表空间使用率未采集到数据' % tags)
            db_tmp_tbs_decute_reason = ''
            db_tmp_tbs_decute = 0
        else:
            db_tmp_tbs_decute_reason = ''
            db_tmp_tbs_decute = 0
            for each_tmp_tbs_stat in tmp_tbs_stat:
                each_tmp_tbs_name = each_tmp_tbs_stat[3]
                each_tmp_tbs_free = float(each_tmp_tbs_stat[4]) - float(each_tmp_tbs_stat[5])
                each_tmp_tbs_used = float(each_tmp_tbs_stat[6])
                db_each_tmp_tbs_decute = tools.get_decute_tmp_tbs(each_tmp_tbs_used, each_tmp_tbs_free)
                if db_each_tmp_tbs_decute <> 0:
                    db_each_tmp_tbs_decute_reason = '%s临时表空间使用率：%d%% 剩余空间：%d \n' % (
                        each_tmp_tbs_name, each_tmp_tbs_used, each_tmp_tbs_free)
                else:
                    db_each_tmp_tbs_decute_reason = ''
                db_tmp_tbs_decute = max(db_tmp_tbs_decute, db_each_tmp_tbs_decute)
                db_tmp_tbs_decute_reason = db_tmp_tbs_decute_reason + db_each_tmp_tbs_decute_reason

        # undo表空间使用率扣分
        undo_tbs_stat = tools.mysql_query(
            "select host,port,service_name,undo_tbs_name,total_mb,used_mb,pct_used from oracle_undo_tbs where tags='%s'" % tags)
        if undo_tbs_stat == 0:
            my_log.logger.warning('%s：undo表空间使用率未采集到数据' % tags)
            db_undo_tbs_decute_reason = ''
            db_undo_tbs_decute = 0
        else:
            db_undo_tbs_decute_reason = ''
            db_undo_tbs_decute = 0
            for each_undo_tbs_stat in undo_tbs_stat:
                each_undo_tbs_name = each_undo_tbs_stat[3]
                each_undo_tbs_free = float(each_undo_tbs_stat[4]) - float(each_undo_tbs_stat[5])
                each_undo_tbs_used = float(each_undo_tbs_stat[6])
                db_each_undo_tbs_decute = tools.get_decute_undo_tbs(each_undo_tbs_used, each_undo_tbs_free)
                if db_each_undo_tbs_decute <> 0:
                    db_each_undo_tbs_decute_reason = "'%s'undo表空间使用率：'%d'%% 剩余空间：%d \n" % (
                        each_undo_tbs_name, each_undo_tbs_used, each_undo_tbs_free)
                else:
                    db_each_undo_tbs_decute_reason = ''
                db_undo_tbs_decute = max(db_undo_tbs_decute, db_each_undo_tbs_decute)
                db_undo_tbs_decute_reason = db_undo_tbs_decute_reason + db_each_undo_tbs_decute_reason

        db_top_decute = max(db_conn_decute,db_archive_decute,db_event_decute, db_tbs_decute, db_cpu_decute, db_mem_decute,db_tmp_tbs_decute,db_undo_tbs_decute)
        db_all_rate = 100 - db_top_decute
        if db_all_rate >= 60:
            db_rate_color = 'green'
            db_rate_level = 'success'
        elif db_all_rate >= 20 and db_all_rate < 60:
            db_rate_color = 'yellow'
            db_rate_level = 'warning'
        else:
            db_rate_color = 'red'
            db_rate_level = 'danger'
        db_all_decute_reason = db_conn_decute_reason + db_archive_decute_reason + db_event_decute_reason + db_tbs_decute_reason + db_cpu_decute_reason + db_mem_decute_reason + db_tmp_tbs_decute_reason + db_undo_tbs_decute_reason

        # 插入总评分及扣分明细
        insert_sql = "insert into oracle_db_rate(tags,host,port,service_name,conn_decute,archive_decute,event_decute,tbs_decute,tmp_decute,undo_decute,cpu_decute,mem_decute,db_rate,db_rate_level,db_rate_color,db_rate_reason) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        value = (
        tags, host, port, service_name, db_conn_decute,db_archive_decute,db_event_decute, db_tbs_decute, db_tmp_tbs_decute,db_undo_tbs_decute,db_cpu_decute, db_mem_decute, db_all_rate,
        db_rate_level, db_rate_color, db_all_decute_reason)
        tools.mysql_exec(insert_sql, value)
        my_log.logger.info('%s扣分明细，连接数扣分:%s，归档使用率扣分：%s, 等待事件扣分：%s, 表空间扣分:%s，临时表空间扣分:%s,Undo表空间扣分:%s,cpu使用率扣分:%s，内存使用率扣分:%s，总评分:%s,扣分原因:%s' %(tags,db_conn_decute,db_archive_decute_reason,db_event_decute_reason,db_tbs_decute,db_tmp_tbs_decute,db_undo_tbs_decute,db_cpu_decute,db_mem_decute,db_all_rate,db_all_decute_reason))
    except Exception, e:
        error_msg = "%s 数据库连接失败：%s" % (tags, unicode(str(e), errors='ignore'))
        db_rate_level = 'red'
        my_log.logger.error(error_msg)
        my_log.logger.info('%s：初始化oracle_db表' % tags)
        insert_sql = "insert into oracle_db_his select * from oracle_db where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_db where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        error_sql = "insert into oracle_db(tags,host,port,service_name,mon_status,rate_level) values(%s,%s,%s,%s,%s,%s)"
        value = (tags, host, port, service_name, 'connected error', db_rate_level)
        tools.mysql_exec(error_sql, value)
        # 更新数据库打分信息
        my_log.logger.info('%s :开始更新数据库评分信息' % tags)
        delete_sql = "delete from oracle_db_rate where tags= '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        insert_sql = "insert into oracle_db_rate(tags,host,port,service_name,db_rate,db_rate_level,db_rate_color,db_rate_reason) select tags,host,port,service_name,'0','danger','red','connected error' from tab_oracle_servers where tags ='%s'" % tags
        tools.mysql_exec(insert_sql, '')
        my_log.logger.info('%s扣分明细，总评分:%s,扣分原因:%s' %(tags,'0','connected error'))


def check_mysql(tags, host,port,user,password):
    my_log.logger.info('等待2秒待Linux主机信息采集完毕')
    time.sleep(2)
    password = base64.decodestring(password)
    try:
        conn = MySQLdb.connect(host=host, user=user, passwd=password, port=int(port), connect_timeout=5, charset='utf8')
        my_log.logger.info('%s：开始获取mysql数据库监控信息' % tags)
        # 归档历史监控数据
        my_log.logger.info('%s：初始化mysql_db表' % tags)
        insert_sql = "insert into mysql_db_his select * from mysql_db where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from mysql_db where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        db_rate_level = 'green'
        # 获取两次状态值
        my_log.logger.info('%s：获取第一次MySQL状态采样' % tags)
        mysql_stat = check_msql.get_mysql_status(conn)
        time.sleep(1)
        my_log.logger.info('%s：获取第二次MySQL状态采样' % tags)
        mysql_stat_next = check_msql.get_mysql_status(conn)

        # 基础信息
        mysql_version = check_msql.get_mysql_para(conn, 'version')
        mysql_uptime = float(mysql_stat['Uptime'])/86400

        # 连接信息
        mysql_max_connections = check_msql.get_mysql_para(conn, 'max_connections')
        current_conn = mysql_stat['Threads_connected']
        threads_running = mysql_stat['Threads_running']
        threads_created = mysql_stat['Threads_created']
        threads_cached = mysql_stat['Threads_cached']
        threads_waited = int(check_msql.get_mysql_waits(conn))

        mysql_conn_rate = "%2.2f" % (float(current_conn) / float(mysql_max_connections))

        # QPS,TPS
        mysql_qps = int(mysql_stat_next['Questions']) - int(mysql_stat['Questions'])
        mysql_tps = int(mysql_stat_next['Com_commit']) - int(mysql_stat['Com_commit'])

        # 流量
        mysql_bytes_received = (int(mysql_stat_next['Bytes_received']) - int(mysql_stat['Bytes_received'])) / 1024
        mysql_bytes_sent = (int(mysql_stat_next['Bytes_sent']) - int(mysql_stat['Bytes_sent'])) / 1024

        # 连接数评级
        conn_rate_level = tools.get_rate_level(float(mysql_conn_rate))

        insert_db_sql = "insert into mysql_db(host,port,tags,version,uptime,max_connections,threads_connected,threads_running,threads_created,threads_cached,threads_waited,conn_rate,conn_rate_level,QPS,TPS,bytes_received,bytes_send,mon_status,rate_level) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        value = (host, port, tags, mysql_version, mysql_uptime, mysql_max_connections, current_conn, threads_running,
                 threads_created, threads_cached, threads_waited, mysql_conn_rate,
                 conn_rate_level, mysql_qps, mysql_tps, mysql_bytes_received, mysql_bytes_sent, 'connected', 'green')
        tools.mysql_exec(insert_db_sql, value)
        my_log.logger.info('%s：获取Mysql数据库监控数据(IP：%s 端口号：%s 连接使用率：%s 连接状态：%s )' % (
            tags, host, port, mysql_conn_rate, 'connected'))

        # 复制
        # 初始化mysql_repl表
        my_log.logger.info('%s：初始化mysql_repl表' % tags)
        insert_sql = "insert into mysql_repl_his select * from mysql_repl where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from mysql_repl where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        server_id = check_msql.get_mysql_para(conn,'server_id')
        is_slave = ''
        is_master = ''
        read_only_result = ''
        master_server = ''
        master_port = ''
        slave_io_run = ''
        slave_io_rate = ''
        slave_sql_run = ''
        slave_sql_rate = ''
        delay = '-'
        delay_rate = ''
        current_binlog_file = ''
        current_binlog_pos = ''
        master_binlog_file = ''
        master_binlog_pos = ''
        master_binlog_space = ''
        curs = conn.cursor()
        master_thread=curs.execute("select * from information_schema.processlist where COMMAND = 'Binlog Dump'")
        slave_stats=curs.execute('show slave status;')
        # 判断Mysql角色
        if master_thread:
            is_master = 'YES'
        if slave_stats:
            is_slave = 'YES'
        mysql_role = ''
        if is_master == 'YES' and is_slave <> 'YES':
            mysql_role = 'master'
        if is_master <> 'YES' and is_slave == 'YES':
            mysql_role = 'slave'
        if is_master == 'YES' and is_slave == 'YES':
            mysql_role = 'master/slave'
        if slave_stats:
            read_only = curs.execute(
                "select * from information_schema.global_variables where variable_name='read_only';")
            read_only_query = curs.fetchone()
            read_only_result = read_only_query[1]
            slave_info = curs.execute("show slave status;")
            slave_result = curs.fetchone()
            master_server = slave_result[1]
            master_port = slave_result[3]
            slave_io_run = slave_result[10]
            if slave_io_run == 'Yes':
                slave_io_rate = 'green'
            else:
                slave_io_rate = 'red'
            slave_sql_run = slave_result[11]
            if slave_sql_run == 'Yes':
                slave_sql_rate = 'green'
            else:
                slave_sql_rate = 'red'
            delay = slave_result[32]


            if delay is None :
                delay_rate = 'red'
            else:
                if int(delay) == 0:
                    delay_rate = 'green'
                elif int(delay) > 0 and int(delay) < 300:
                    delay_rate = 'yellow'
                else:
                    delay_rate = 'red'

            current_binlog_file=slave_result[9]
            current_binlog_pos=slave_result[21]
            master_binlog_file=slave_result[5]
            master_binlog_pos=slave_result[6]
        elif master_thread:
            read_only = curs.execute(
            "select * from information_schema.global_variables where variable_name='read_only';")
            read_only_query = curs.fetchone()
            read_only_result = read_only_query[1]
            master_info = curs.execute('show master status;')
            master_result = curs.fetchone()
            master_binlog_file = master_result[0]
            master_binlog_pos = master_result[1]
        if master_thread:
            binlog_file = curs.execute('show master logs;')
            binlogs = 0
            if binlog_file:
                for row in curs.fetchall():
                    binlogs = binlogs + row[1]
            master_binlog_space = int(binlogs)/1024/1024

        insert_repl_sql = "insert into mysql_repl(tags,server_id,host,port,is_master,is_slave,mysql_role,read_only,master_server,master_port,slave_io_run,slave_io_rate,slave_sql_run,slave_sql_rate,delay,delay_rate,current_binlog_file,current_binlog_pos,master_binlog_file,master_binlog_pos,master_binlog_space) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        value = (tags,server_id,host,port,is_master,is_slave,mysql_role,read_only_result,master_server,master_port,slave_io_run,slave_io_rate,slave_sql_run,slave_sql_rate,delay,delay_rate,current_binlog_file,current_binlog_pos,master_binlog_file,master_binlog_pos,master_binlog_space)
        tools.mysql_exec(insert_repl_sql, value)
        my_log.logger.info('%s：获取Mysql数据库复制数据' %tags)


        # 更新数据库打分信息
        my_log.logger.info('%s :开始更新Mysql数据库评分信息' % tags)
        delete_sql = "delete from mysql_db_rate where tags= '%s'" % tags
        tools.mysql_exec(delete_sql, '')

        # 内存使用率扣分
        db_mem_decute = 0
        db_mem_decute_reason = ''
        mem_stat = tools.mysql_query(
            "select host,host_name,mem_used from os_info where mem_used is not null and host = '%s'" % host)
        if mem_stat == 0:
            my_log.logger.warning('%s：内存使用率未采集到数据' % host)
            db_mem_decute = 0
        else:
            db_mem_used = float(mem_stat[0][2])
            db_mem_decute = tools.get_decute(db_mem_used)
            if db_mem_decute <> 0:
                db_mem_decute_reason = '内存使用率：%d%% \n' % db_mem_used
            else:
                db_mem_decute_reason = ''

        # cpu使用率扣分
        db_cpu_decute_reason = ''
        cpu_stat = tools.mysql_query(
            "select host,host_name,cpu_used from os_info where cpu_used is not null and host = '%s'" % host)
        if cpu_stat == 0:
            my_log.logger.warning('%s：CPU使用率未采集到数据' % host)
            db_cpu_decute = 0
        else:
            db_cpu_used = float(cpu_stat[0][2])
            db_cpu_decute = tools.get_decute(db_cpu_used)
            if db_cpu_decute <> 0:
                db_cpu_decute_reason = 'CPU使用率：%d%% \n' % db_cpu_used
            else:
                db_cpu_decute_reason = ''

        # 连接数扣分
        db_conn_decute = 0
        db_conn_decute_reason = ''
        db_conn_decute = tools.get_decute(float(mysql_conn_rate))
        if db_conn_decute <> 0:
            db_conn_decute_reason = '连接数：%d%% \n' % mysql_conn_rate
        else:
            db_conn_decute_reason = ''

        db_top_decute = max(db_conn_decute, db_cpu_decute, db_mem_decute)
        db_all_rate = 100 - db_top_decute
        if db_all_rate >= 60:
            db_rate_color = 'green'
            db_rate_level = 'success'
        elif db_all_rate >= 20 and db_all_rate < 60:
            db_rate_color = 'yellow'
            db_rate_level = 'warning'
        else:
            db_rate_color = 'red'
            db_rate_level = 'danger'
        db_all_decute_reason = db_conn_decute_reason + db_cpu_decute_reason + db_mem_decute_reason

        # 插入总评分及扣分明细
        insert_sql = "insert into mysql_db_rate(host,port,tags,conn_decute,cpu_decute,mem_decute,db_rate,db_rate_level,db_rate_color,db_rate_reason) select host,port,tags,'%s','%s','%s','%s','%s','%s','%s' from tab_mysql_servers where tags ='%s'" % (
            db_conn_decute, db_cpu_decute, db_mem_decute, db_all_rate, db_rate_level, db_rate_color,
            db_all_decute_reason, tags)
        tools.mysql_exec(insert_sql, '')
        my_log.logger.info('%s扣分明细，连接数扣分:%s，cpu使用率扣分:%s，内存使用率扣分:%s，总评分:%s,扣分原因:%s' %(tags,db_conn_decute,db_cpu_decute,db_mem_decute,db_all_rate,db_all_decute_reason))


    except Exception, e:
        error_msg = "%s mysql数据库连接失败：%s" % (tags, unicode(str(e), errors='ignore'))
        db_rate_level = 'red'
        my_log.logger.error(error_msg)
        my_log.logger.info('%s：初始化mysql_db表' % tags)
        insert_sql = "insert into mysql_db_his select * from mysql_db where tags = '%s'" % tags
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from mysql_db where tags = '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        error_sql = "insert into mysql_db(host,port,tags,mon_status,rate_level) values(%s,%s,%s,%s,%s)"
        value = (host, port, tags, 'connected error',db_rate_level)
        tools.mysql_exec(error_sql, value)
        # 更新数据库打分信息
        my_log.logger.info('%s :开始更新数据库评分信息' %tags)
        delete_sql = "delete from mysql_db_rate where tags= '%s'" % tags
        tools.mysql_exec(delete_sql, '')
        insert_sql = "insert into mysql_db_rate(host,port,tags,db_rate,db_rate_level,db_rate_color,db_rate_reason) select host,port,tags,'0','danger','red','connected error' from tab_mysql_servers where tags ='%s'" % tags
        tools.mysql_exec(insert_sql, '')
        my_log.logger.info('%s扣分明细，总评分:%s,扣分原因:%s' %(tags,'0','conected error'))




if __name__ =='__main__':
    while True:
        check_sleep_time = float(conf.get("policy", "check_sleep_time"))
        # 清空linux无效监控数据
        my_log.logger.info('清除osinfo表无效监控数据')
        insert_sql = "insert into os_info_his select * from os_info where tags not in (select tags from tab_linux_servers)"
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from os_info where tags not in (select tags from tab_linux_servers)"
        tools.mysql_exec(delete_sql, '')
        # 文件系统监控
        my_log.logger.info('清除os_filesystem表无效监控数据')
        insert_sql = "insert into os_filesystem_his select * from os_filesystem  where tags not in (select tags from tab_linux_servers)"
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from os_filesystem where tags not in (select tags from tab_linux_servers)"
        tools.mysql_exec(delete_sql, '')

        # 清空无效监控数据
        my_log.logger.info('清除oracle_tbs表无效监控数据')
        insert_sql = "insert into oracle_tbs_his select * from oracle_tbs where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_tbs where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(delete_sql, '')
        my_log.logger.info('清除oracle_db表无效监控数据')
        insert_sql = "insert into oracle_db_his select * from oracle_db where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_db where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(delete_sql, '')
        my_log.logger.info('清除oracle_db_event表无效监控数据')
        insert_sql = "insert into oracle_db_event_his select * from oracle_db_event where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_db_event where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(delete_sql, '')
        my_log.logger.info('清除oracle_temp_tbs表无效监控数据')
        insert_sql = "insert into oracle_tmp_tbs_his select * from oracle_tmp_tbs where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_tmp_tbs where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(delete_sql, '')
        my_log.logger.info('清除oracle_undo_tbs表无效监控数据')
        insert_sql = "insert into oracle_undo_tbs_his select * from oracle_undo_tbs where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_undo_tbs where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(delete_sql, '')
        my_log.logger.info('清除oracle_db_rate表无效监控数据')
        insert_sql = "insert into oracle_db_rate_his select * from oracle_db_rate where tags not in (select tags from tab_oracle_servers)"
        # tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from oracle_db_rate where tags not in (select tags from tab_oracle_servers)"
        tools.mysql_exec(delete_sql, '')
        my_log.logger.info('清除mysql_db_rate表无效监控数据')
        insert_sql = "insert into mysql_db_rate_his select * from mysql_db_rate where tags not in (select tags from tab_mysql_servers)"
        # tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from mysql_db_rate where tags not in (select tags from tab_mysql_servers)"
        tools.mysql_exec(delete_sql, '')
        my_log.logger.info('清除mysql_db_repl表无效监控数据')
        insert_sql = "insert into mysql_repl_his select * from mysql_repl where tags not in (select tags from tab_mysql_servers)"
        # tools.mysql_exec(insert_sql, '')
        delete_sql = "delete from mysql_repl where tags not in (select tags from tab_mysql_servers)"
        tools.mysql_exec(delete_sql, '')

        linux_servers = tools.mysql_query('select tags,host,host_name,user,password from tab_linux_servers')
        oracle_servers = tools.mysql_query(
            'select tags,host,port,service_name,user,password,user_os,password_os from tab_oracle_servers')
        mysql_servers = tools.mysql_query(
            'select tags,host,port,user,password,user_os,password_os from tab_mysql_servers')

        p_pool = []
        if linux_servers:
            for i in xrange(len(linux_servers)):
                l_server = Process(target=check_linux, args=(
                    linux_servers[i][0], linux_servers[i][1], linux_servers[i][2], linux_servers[i][3],linux_servers[i][4]))
                l_server.start()
                my_log.logger.info('%s 开始采集Linux主机信息' %linux_servers[i][0])
                p_pool.append(l_server)
        if oracle_servers:
            for i in xrange(len(oracle_servers)):
                o_server = Process(target=check_oracle, args=(
                    oracle_servers[i][0], oracle_servers[i][1], oracle_servers[i][2], oracle_servers[i][3],
                    oracle_servers[i][4], oracle_servers[i][5], oracle_servers[i][6],oracle_servers[i][7]))
                o_server.start()
                my_log.logger.info('%s 开始采集oracle数据库信息' %oracle_servers[i][0])
                p_pool.append(o_server)
        if mysql_servers:
            for i in xrange(len(mysql_servers)):
                m_server = Process(target=check_mysql, args=(
                    mysql_servers[i][0], mysql_servers[i][1], mysql_servers[i][2], mysql_servers[i][3],
                    mysql_servers[i][4]))
                m_server.start()
                my_log.logger.info('%s 开始采集mysql数据库信息' %mysql_servers[i][0])
                p_pool.append(m_server)

        for each_server in p_pool:
            each_server.join()
        # 告警
        alarm.alarm()

        my_log.logger.info('%s 秒后开始下一次轮询' %check_sleep_time)
        time.sleep(check_sleep_time)







