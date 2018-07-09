from sys import argv, exit, stderr
from collections import Counter

from server import db, Article, User, Experiment, Feedback


def main() :
    c = Counter()
    for ex in Experiment.query.all() :
        c[ex.user.name] += 1

    if not c :
        print >> stderr, "no users found in database"
        return 1

    num_ex = max(c.values())
    #print >> stderr, " --> %d experiments per user" % num_ex

    f_use = open('user_table.txt', 'w')
    print >> f_use, "username email gender age edu_years pg_degree ug_degree language lang_years google_scholar arxiv researchgate acm_webofscience other q1 q2 q3 q4 q5 q6 q7 q8 q9 q10"

    f_exp = open('feedback_table.txt', 'w')
    print >> f_exp, "username search_term feedback_type article_id feedback"

    f_que = open('experiment_table.txt', 'w')
    print >> f_que, "username search_term feedback_type q1 q2 q3 timetaken"

    user_count = 0
    experiment_count = 0
    for name in c :
        if c[name] != num_ex :
            continue

        user = User.query.filter_by(name=name).first()

        print >> f_use, user.name, user.email, user.gender, user.age, \
                user.edu_years, user.pg_degree.replace(' ', '_'), user.ug_degree.replace(' ', '_'), \
                user.language.replace(' ','_'), user.lang_years, \
                user.sls_google, user.sls_arxiv, user.sls_rg, user.sls_acm, user.sls_other, \
                str(user.q1).replace(' ', '_'), \
                str(user.q2).replace(' ', '_'), \
                str(user.q3).replace(' ', '_'), \
                str(user.q4).replace(' ', '_'), \
                str(user.q5).replace(' ', '_'), \
                str(user.q6).replace(' ', '_'), \
                str(user.q7).replace(' ', '_'), \
                str(user.q8).replace(' ', '_'), \
                str(user.q9).replace(' ', '_'), \
                str(user.q10).replace(' ', '_')

        user_count += 1
        prev_time = user.timestamp
        for ex in Experiment.query.filter_by(user_id=user.id) :
            experiment_count += 1
            
            print >> f_que, user.name, ex.search_term.replace(' ', '_'), \
                    "positive" if ex.positive else "negative", \
                    str(ex.q1).replace(' ', '_'), \
                    str(ex.q2).replace(' ', '_'), \
                    str(ex.q3).replace(' ', '_'), \
                    int((ex.timestamp - prev_time).total_seconds())

            prev_time = ex.timestamp

            for fb in Feedback.query.filter_by(experiment_id=ex.id) :
                print >> f_exp, user.name, ex.search_term.replace(' ', '_'), "positive" if ex.positive else "negative", fb.article_id, fb.feedback

    f_use.close()
    print >> stderr, "written", f_use.name
    f_exp.close()
    print >> stderr, "written", f_exp.name
    f_que.close()
    print >> stderr, "written", f_que.name
    
    #print >> stderr, " --> %d users" % user_count
    #print >> stderr, " --> %d experiments" % experiment_count
    print >> stderr, "done!"
    return 0

if __name__ == '__main__' :
    try :
        exit(main())
    except KeyboardInterrupt :
        print >> stderr, "Killed by User...\n"
        exit(1)

