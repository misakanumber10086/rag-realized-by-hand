
import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeAlias


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

#这一块涉及到python的一个新知识点
#类型注释：
#        python和C++不一样，C++中每个不同的数据必须用特定的变量才能接收，而python的变量可以接收任意格式的数据。
#        这就导致别人会对某个变量需要接收的数据类型感到疑惑，所以就有了这个类型注释。
#        就是在解释某个变量需要接收哪一种数据类型。
#        这种方式还有一个特殊的效果，可以在全局创建一个数据变量

#这一块的逻辑：
#            其实函数传参的类型注释和一块是相同的效果
#            而这里不使用函数传参的形式，而是专门运用了类型注释的原因是
#            这几个数据需要保存到全局
DatasetItem: TypeAlias = dict[str, Any]
#这个数据用来存
# 某一个问题      对应的需要引用的chunks的ID
#                本身  
#                类别
#                难度
# 例子：
#{
#    "question": "什么是软件工程？",
#    "expected_chunks": [29],
#    "category": "基础概念",
#    "difficulty": "简单"
#}
RetrievalResult: TypeAlias = dict[str, Any]
# 智能客服对某一个问题的      实际检索的结果即：
#                           都有哪些chunks被检索到了 
# 例子：
#{
#    "question": "什么是软件工程？",
#    "retrieved_chunks": [29, 35, 48]
#}     
OverallReport: TypeAlias = dict[str, int | float]
# 这个字典集需要存五个数据类型：
#                           1. 总共有多少道题目，总问题数       dataset_size
#                           2. 实际评测了多少道题目，实际评测数         evaluated_size
#                           3. 命中率：指正确的对应的chunks被检索出来的平均概率       recall_at_k
#                           4. 召回率：指至少命中了一个chunks的问题         query_hit_rate_at_k
#                           5. 缺少结果的题目数         missing_questions
GroupedReport: TypeAlias = dict[str, dict[str, int | float]]
#这个嵌套字典集主要是为了将总的召回率和命中率根据不同的难度分成三种
#类似这样：
#{
#    "基础概念 / 简单": {
#        "count": 10,
#        "recall_at_k": 0.8,
#        "query_hit_rate_at_k": 0.9
#    },
#    "需求分析 / 困难": {
#        "count": 5,
#        "recall_at_k": 0.6,
#        "query_hit_rate_at_k": 0.8
#    }
#}
DetailReport: TypeAlias = dict[str, Any]
#这是保存每一道题的详细评测结果：
#                            题目具体是什么
#                            是否召回
#                            命中率
#                            预期的chunks
#                            被召回的chunks

def recall(expected: Iterable[int], retrieved: Iterable[int]) -> float:#这里传参，只把问题的ID传了过来
    expected_set = set(expected)
    retrieved_set = set(retrieved)
    return len(expected_set & retrieved_set) / len(expected_set) if expected_set else 0.0
    #这个地方利用到了python中的一个新知识点
    #集合：
    #   1. 集合与数组的区别：
    #                     (a) 集合中的元素没有顺序
    #                     (b) 集合中的元素不可以重复
    #   2. 集合的小知识点: 
    #                   (a) 虽然集合中的元素没有顺序，但是同样可以用for循环来遍历集合中的元素，只不过遍历的顺序是随机的
    #                   (b) 如果想验证集合中的特定元素可以使用 in 来验证，例如： 1 in {1, 2, 3} 返回 True， 4 in {1, 2, 3} 返回 False
    #                   (c) 集合可以进行数学运算，例如：交集、并集、差集等
    #                   (d) 集合可以使用 set() 来创建，例如：set([1, 2, 3]) 返回 {1, 2, 3}。当然set中传入的参数必须是可迭代数据
    #                   (e) 集合可以用sorted()函数来转化成为列表，当然，直接用list()函数也可以
    #这个函数的逻辑：
    #              首先用set函数将两个列表转化成函数
    #              然后用 & 运算符来求两个集合的交集,得出两个共同的地方
    #              最后用len()函数来求出交集的长度，然后除以expected_set的长度，得出召回率

def evaluate(dataset: list[DatasetItem], results: list[RetrievalResult], k: int) -> tuple[OverallReport, GroupedReport, list[DetailReport], list[str]]:
    by_question = {row["question"]: row for row in results}
    #这个by_question的逻辑是：
    #                       将row从这个字典数组(系统实际测试的问题)中取出来
    #                       然后用row这个字典中的键"question"对应的值来当一个新的键
    #                       让他去对应row这个字典本身
    #                       所以创建出来的就是一个   "值是字典的字典"
    #这是个非常nb的技巧。让字典中的一个元素去对应该字典。因为字典是没有名字的，如果我们想找到某个字典的数据是很难的。
    #这种方式帮助我们更容易找到字典
    scores: float = []
    groups = defaultdict(list)
    #defaultdict(函数which可以不传参就调用)
    #           这是python内部的一个造字典的方法，只不过，这个造字典的方法可以让字典像列表一样可以整一个动态的大小
    #           原理是：
    #                  例如a = defaultdict(list)会返回一个字典
    #                  当你引用该字典中不存在的数据时，例如：
    #                  a["不存在的元素"]。这时他会返回一个空的列表
    #                  那么这时，如果你使用append()函数就可以往里添加一个键值对
    #                  a["不存在的元素"].append("不存在的元素对应的值")
    #                  其他的方法也可以：例如
    #                  a = defaultdict(int) 的话
    #                  可以  a["不存在的元素"] += 1
    #                  a = defaultdict(string) 的话
    #                  可以  a["不存在的元素"] += "abc"
    details: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for item in dataset:
        result = by_question.get(item["question"])
        #这个地方就是之前我说的给字典起名的好处了，可以直接根据dataset中的question对应到一个字典
        if result is None:
            missing.append(item["question"])
            continue
        retrieved = result.get("retrieved_chunks")
        score = recall(item["expected_chunks"], retrieved[:k])#这个k是限制了只看系统返回的前k项chunks
        scores.append(score)
        groups[(item["category"], item["difficulty"])].append(score)#这个地方也是个很好的技巧，可以使两个键合起来对应一个值，其实是利用了元组会被当成常量的特性
        details.append({
            "question": item["question"],
            "recall": score,
            "hit": score > 0,
            "expected_chunks": item["expected_chunks"],
            "retrieved_at_k": retrieved[:k],
        })

    overall = {
        "dataset_size": len(dataset),
        "evaluated_size": len(scores),
        "recall_at_k": sum(scores) / len(scores) if scores else 0.0,
        "query_hit_rate_at_k": sum(s > 0 for s in scores) / len(scores) if scores else 0.0,
        "missing_questions": len(missing),
    }
    grouped = {
        f"{category} / {difficulty}": {
            "count": len(values),
            "recall_at_k": sum(values) / len(values),
            "query_hit_rate_at_k": sum(v > 0 for v in values) / len(values),
        }
        for (category, difficulty), values in sorted(groups.items())
    }
    return overall, grouped, details, missing



def print_report(overall: OverallReport, grouped: GroupedReport, k: int, missing: list[str]) -> None:
    print(f"样本数: {overall['dataset_size']}")
    print(f"已评测: {overall['evaluated_size']}")
    print(f"Recall@{k}: {overall['recall_at_k']:.4f}")
    print(f"Query 命中率@{k}: {overall['query_hit_rate_at_k']:.4f}")
    if missing:
        print(f"缺少结果: {len(missing)} 条")
    print("\n按类别/难度:")
    for name, values in grouped.items():
        print(
            f"- {name}: Recall@{k}={values['recall_at_k']:.4f}, "
            f"命中率={values['query_hit_rate_at_k']:.4f} ({values['count']} 条)"
        )


def retrieve(question: str, top_k: int = 5, *, item: DatasetItem | None = None, demo: bool = False, index: Any | None = None) -> list[int]:
    #这里的*是一个传参小技巧，用来防止后面的参数传错，
    #* 后面的参数必须使用“参数名=值”的方式传入，不能只按位置传入。
    
    if demo:
        # 仅用于验证评测流程；不代表真实检索效果。
        return item["expected_chunks"][:top_k]
    return [result["chunk_id"] for result in index.search(question)[:top_k]]


def main() -> None:
    #下面是一个类似设置环境变量的过程
    #详细解析
    parser = argparse.ArgumentParser(description="批量生成检索结果并计算 Recall@K")
    parser.add_argument("--dataset", default="知识库评测数据集.json")
    parser.add_argument("--output", default="retrieval_results.json")#这一行决定了系统的“原始的未经加工的返回结果”（其实就是主文件app.py中search返回的结果，不涉及该文件中返回的结果）要放在哪一个文件里
    parser.add_argument("--report", default="recall_report.json")#这一行决定了该文件“进行加工过的文件返回的结果”（也就是evaluate方程返回的结果）要放在哪一个方程里
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="只评测前 N 条; 0 表示全部")
    parser.add_argument("--demo", action="store_true", help="使用标准答案模拟检索，仅验证流程")
    args = parser.parse_args()

    if args.k <= 0:
        parser.error("--k 必须是正整数")
    if args.limit < 0:
        parser.error("--limit 不能为负数")

    base = HERE
    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = base / dataset_path
    with open(dataset_path, encoding="utf-8") as f:
        full_dataset = json.load(f)

    dataset = full_dataset[: args.limit] if args.limit else full_dataset
    retrieval_index = None#这个None不用担心，他是给demo用的，当开始真正的检索过程的时候，它会被重新赋值
    if not args.demo:
        import app

        retrieval_index = app.LocalIndex(app.Data_location)
        retrieval_index.extract_and_process()
        print(f"已按 app.py 的规则加载 {len(retrieval_index.chunks)} 个 chunk\n")

    results = []
    for item_index, item in enumerate(dataset, 1):
        chunks = retrieve(
            item["question"],
            args.k,
            item=item,
            demo=args.demo,
            index=retrieval_index,
        )
        results.append({"question": item["question"], "retrieved_chunks": chunks})
        print(f"已处理 {item_index}/{len(dataset)}: {item['question']}")

    output_path = Path(args.output)
    report_path = Path(args.report)
    if not output_path.is_absolute():
        output_path = base / output_path
    if not report_path.is_absolute():
        report_path = base / report_path

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    overall, grouped, details, missing = evaluate(dataset, results, args.k)
    print("\n评测结果")
    print_report(overall, grouped, args.k, missing)

    report = {"k": args.k, "overall": overall, "by_group": grouped, "details": details}
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n检索结果已保存: {output_path}")
    print(f"评测报告已保存: {report_path}")


if __name__ == "__main__":
    main()
