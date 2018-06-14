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
    print >> f_use, "username email gender relevance q1 q2 q3 q4 q5"

    f_exp = open('experiment_table.txt', 'w')
    print >> f_exp, "username search_term article_id feedback"

    user_count = 0
    experiment_count = 0
    for name in c :
        if c[name] != num_ex :
            continue

        user = User.query.filter_by(name=name).first()

        print >> f_use, user.name, user.email, user.gender, \
            user.relevance.replace(' ', '_'), \
            user.q1.replace(' ', '_'), \
            user.q2.replace(' ', '_'), \
            user.q3.replace(' ', '_'), \
            user.q4.replace(' ', '_'), \
            user.q5.replace(' ', '_')

        user_count += 1
        for ex in Experiment.query.filter_by(user_id=user.id) :
            experiment_count += 1
            for fb in Feedback.query.filter_by(experiment_id=ex.id) :
                print >> f_exp, user.name, ex.search_term.replace(' ', '_'), fb.article_id, fb.feedback != ex.positive 

    f_use.close()
    print >> stderr, "written", f_use.name
    f_exp.close()
    print >> stderr, "written", f_exp.name
    
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

