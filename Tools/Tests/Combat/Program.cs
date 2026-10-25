using System.Text.Json;
using System.Text.Json.Nodes;
using GameScripts.Survivor;
string text=File.ReadAllText(args[0]);
var game=new WebGameSession(text,"");game.FixtureCrowd(320,200);
Console.WriteLine(JsonSerializer.Serialize(game.FixtureBenchmark()));
#if !BASELINE
game.FixtureCrowd(320,0);game.FixtureCheckQueries();game.FixtureRegionBurst();game.FixtureMobileLimit();
var a=new WebGameSession(text,"");var b=new WebGameSession(text,"");a.FixtureCrowd(40,0,true);b.FixtureCrowd(40,0,true);
if(args.Length>1){Directory.CreateDirectory(args[1]);File.WriteAllText(Path.Combine(args[1],"crowd-before.json"),a.Snapshot());}
if(a.FixtureSeparate()!=b.FixtureSeparate())throw new Exception("Separation is not deterministic");
if(args.Length>1)File.WriteAllText(Path.Combine(args[1],"crowd-after.json"),a.Snapshot());
a.FixtureCrowd(80,0);b.FixtureCrowd(80,0);var limited=a.FixtureVisuals(128);var full=b.FixtureVisuals(int.MaxValue);
if(limited.Visuals!=176||full.Visuals!=2448||limited.Health!=full.Health)throw new Exception("Visual budget changed damage or hostile cues");
var catalog=JsonNode.Parse(text)!;
if((double)catalog["objective"]!["outsideGraceSeconds"]!!=2)throw new Exception("Grace not adjusted");
if((double)CharacterRules.CompileStartState("fixture",new CharacterDefinition())["move_speed"]!=5.1)throw new Exception("Base speed mismatch");
var mover=new WebGameSession(text,"");mover.Command("start","");var state=JsonNode.Parse(mover.Step(.05,1,0))!;
if(Math.Abs((double)state["x"]!-5.1*1.08*.05)>1e-8)throw new Exception("Movement delta not scaled correctly");
Console.WriteLine("unit-test PASS: 500 random nearest/collision-order queries, exact density targeting, deterministic bounded crowd separation/freeze, visual damage parity and hostile cue preservation, +20% movement");
#endif
