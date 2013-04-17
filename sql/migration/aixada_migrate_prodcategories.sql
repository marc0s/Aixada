-- added categories for socarrel
insert into aixada_product_category values (1500, 'prdcat_legumes');
insert into aixada_product_category values (1600, 'prdcat_eatseeds');
insert into aixada_product_category values (14100, 'prdcat_sauces');
insert into aixada_product_category values (14200, 'prdcat_oilandvinegar');
insert into aixada_product_category values (19100, 'prdcat_driedfruits');
update aixada_product_category set description = 'prdcat_meat_eggs' where id = 5000;

