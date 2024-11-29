from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from sqlmodel import Session, select, func
from database.connection import get_db
from models.users import User
from models.post import Post
from models.like import Like
from models.offer import Offer
from models.post import PostCreate, SoldPriceRequest, PostUpdate
from models.offer import OfferCreate, OfferAcceptRequest
from models.like import LikeCreate
from datetime import datetime
from sqlalchemy import delete

post_router = APIRouter()

@post_router.get("/ranking")
def get_ranking(db: Session = Depends(get_db)):
    try:
        query = select(Post).order_by(Post.sold_price.desc()).limit(10)
        posts = db.exec(query).all()
        return [post.dict() for post in posts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@post_router.get("/recent-posts")
def get_recent_posts(db: Session = Depends(get_db)):
    try:
        query = select(Post).order_by(Post.created_date.desc()).limit(8)
        posts = db.exec(query).all()
        return [post.dict() for post in posts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@post_router.get("/like-ranking")
def get_like_ranking(db: Session = Depends(get_db)):
    try:
        query = (
            select(Post, func.count(Like.post_id).label("like_count"))
            .join(Like, Post.id == Like.post_id)
            .group_by(Post.id)
            .order_by(func.count(Like.post_id).desc())
            .limit(10)
        )
        results = db.exec(query).all()

        return [
            {**post.dict(), "like_count": like_count} for post, like_count in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# posts/create 게시글 생성
@post_router.post("/create", response_model=dict)
def create_post(post_data: PostCreate, db: Session = Depends(get_db)):
    try:
        new_post = Post(
            user_id=post_data.user_id,
            item_name=post_data.item_name,
            expected_price=post_data.expected_price,
            created_date=datetime.now(),
            updated_date=datetime.now(),
            dna=post_data.dna,
            img_url=post_data.img_url,
            is_sold=False,
            description=post_data.description,
            sold_price=0.0
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        return {
            "message": "Post created successfully",
            "post": {
                "id": new_post.id,
                "user_id": new_post.user_id,
                "item_name": new_post.item_name,
                "expected_price": new_post.expected_price,
                "created_date": new_post.created_date,
                "updated_date": new_post.updated_date,
                "dna": new_post.dna,
                "img_url": new_post.img_url,
                "is_sold": new_post.is_sold,
                "description": new_post.description,
                "sold_price": new_post.sold_price
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create post: {str(e)}"
        )
    

# 특정 상품 데이터 가져오기 엔드포인트
@post_router.get("/{id}", response_model=dict)
def get_post(id: int, db: Session = Depends(get_db)):
    post = db.exec(select(Post).where(Post.id == id)).first()
    offers = db.exec(select(Offer).where(Offer.post_id == id)).all()
    user = db.exec(select(User).where(User.id == post.user_id)).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    offers_list = []
    for offer in offers:
        # Get user for each offer
        offer_user = db.exec(select(User).where(User.id == offer.user_id)).first()
        
        offer_dict = {
            "id": offer.id,
            "user_id": offer.user_id,
            "post_id": offer.post_id,
            "offer_price": offer.offer_price,
            "created_date": offer.created_date,
            "dna": offer.dna,
            "is_accepted": offer.is_accepted,
            "email": offer_user.email if offer_user else None  # None if user not found
        }
        offers_list.append(offer_dict)

    return {
        "post": {   
            "id": post.id,
            "user_id": post.user_id,
            "item_name": post.item_name,
            "expected_price": post.expected_price,
            "created_date": post.created_date,
            "updated_date": post.updated_date,
            "dna": post.dna,
            "img_url": post.img_url,
            "is_sold": post.is_sold,
            "description": post.description,
            "sold_price": post.sold_price,
        },
        "user_info":{
            "id" : user.id,
            "email" : user.email,
            "nickname" : user.nickname,
        },
        "offers": offers_list,  # Offer 목록 추가

    }

# 판매되었을때 판매여부 상태 변경
@post_router.put("/{id}/sold", response_model=dict)
def update_post_sold_status(
    id: int,
    request: SoldPriceRequest,
    db: Session = Depends(get_db)
):
    post = db.exec(select(Post).where(Post.id == id)).first()
    print("판매진입")
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.is_sold = True
    post.sold_price = request.sold_price
    db.add(post)
    db.commit()
    db.refresh(post)
    
    return {
        "message": "Successfully updated sold status",
        "post": {
            "id": post.id,
            "item_name": post.item_name,
            "is_sold": post.is_sold,
            "sold_price": post.sold_price
        }
    }

# offer 내역 저장
@post_router.post("/{id}/offer", response_model=dict)
def create_offer(
    id: int,
    offer_data: OfferCreate, 
    db: Session = Depends(get_db)
):
    try:
        # Validate if path parameter matches body post_id
        if id != offer_data.post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path id does not match body post_id"
            )
        
        # Check if post exists
        post = db.exec(select(Post).where(Post.id == id)).first()

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        # Check if post is already sold
        
        if post.is_sold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post is already sold"
            )
        # Find user by email
        user = db.exec(select(User).where(User.email == offer_data.user_email.replace('"', ''))).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with provided email not found"
            )
        # Create new offer
        new_offer = Offer(
            user_id=user.id,
            post_id=id,
            offer_price=offer_data.offer_price,
            created_date=datetime.now(),
            is_accepted=False
        )

        db.add(new_offer)
        db.commit()
        db.refresh(new_offer)

        return {
            "message": "Offer created successfully",
            "offer": {
                "id": new_offer.id,
                "user_id": new_offer.user_id,
                "user_email": user.email,
                "post_id": new_offer.post_id,
                "offer_price": new_offer.offer_price,
                "created_date": new_offer.created_date,
                "is_accepted": new_offer.is_accepted
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create offer: {str(e)}"
        )

@post_router.put("/{post_id}/accept", response_model=dict)
def accept_offer(
    post_id: int,
    request: OfferAcceptRequest,
    db: Session = Depends(get_db)
):
    print("1")
    try:
        # 게시글 존재 여부 확인
        post = db.exec(select(Post).where(Post.id == post_id)).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        print("11")
        # 이미 판매된 게시글인지 확인
        if post.is_sold:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post is already sold"
            )
        print("111")
        # 제안 존재 여부 확인
        offer = db.exec(select(Offer).where(Offer.id == request.offer_id)).first()
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offer not found"
            )
        print("1111")
        # 제안이 해당 게시글의 것인지 확인
        if offer.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offer does not belong to this post"
            )
        print("11111")
        # 이미 수락된 제안이 있는지 확인
        existing_accepted_offer = db.exec(
            select(Offer).where(
                (Offer.post_id == post_id) & 
                (Offer.is_accepted == True)
            )
        ).first()
        print("6")
        if existing_accepted_offer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another offer is already accepted"
            )
        print("7")
        # 제안자 정보 조회
        user = db.exec(select(User).where(User.id == offer.user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offer user not found"
                )
        print("8")
        # 제안 수락 상태 변경
        offer.is_accepted = True
        # post.offer_accepted = True
        print("110")
        db.add(offer)
        db.add(post)
        db.commit()
        db.refresh(offer)
        print("9")
        return {
            "message": "Offer accepted successfully",
            "offer": {
                "id": offer.id,
                "user_id": offer.user_id,
                "user_email": user.email,
                "post_id": offer.post_id,
                "offer_price": offer.offer_price,
                "created_date": offer.created_date,
                "is_accepted": offer.is_accepted
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept offer: {str(e)}"
        )


# 좋아요 토글
@post_router.post("/{id}/like", response_model=dict)
def toggle_like(
    id: int,
    like_data: LikeCreate,
    db: Session = Depends(get_db)
):
    try:
        # Validate if path parameter matches body post_id
        if id != like_data.post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path id does not match body post_id"
            )

        # Check if post exists
        post = db.exec(select(Post).where(Post.id == id)).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
            
        # Find user by email
        user = db.exec(select(User).where(User.email == like_data.user_email.replace('"', ''))).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with provided email not found"
            )

        # Check if like already exists
        existing_like = db.exec(
            select(Like).where(
                (Like.user_id == user.id) & 
                (Like.post_id == id)
            )
        ).first()

        # If like exists, delete it (unlike)
        if existing_like:
            db.delete(existing_like)
            db.commit()
            return {
                "message": "Like removed successfully",
                "action": "unliked",
                "like": {
                    "id": existing_like.id,
                    "user_id": existing_like.user_id,
                    "post_id": existing_like.post_id
                }
            }

        # If like doesn't exist, create new like
        new_like = Like(
            user_id=user.id,
            post_id=id
        )

        db.add(new_like)
        db.commit()
        db.refresh(new_like)

        return {
            "message": "Like created successfully",
            "action": "liked",
            "like": {
                "id": new_like.id,
                "user_id": new_like.user_id,
                "post_id": new_like.post_id
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle like: {str(e)}"
        )
    
@post_router.get("/{id}/like/check", response_model=dict)
def check_like_status(
    id: int,
    user_email: str,
    db: Session = Depends(get_db)
):
    try:
        # Check if post exists
        post = db.exec(select(Post).where(Post.id == id)).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
            
        # Find user by email
        user = db.exec(select(User).where(User.email == user_email.replace('"', ''))).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if like exists
        existing_like = db.exec(
            select(Like).where(
                (Like.user_id == user.id) & 
                (Like.post_id == id)
            )
        ).first()
        
        return {
            "liked": existing_like is not None
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check like status: {str(e)}"
        )
    

    # 게시글 삭제 엔드포인트
@post_router.delete("/{id}/delete")
def delete_post(id: int, db: Session = Depends(get_db)):
    try:
        # 게시글 존재 여부 확인
        post = db.exec(select(Post).where(Post.id == id)).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # 연관된 like와 offer도 함께 삭제
        db.exec(delete(Like).where(Like.post_id == id))
        db.exec(delete(Offer).where(Offer.post_id == id))
        
        # 게시글 삭제
        db.delete(post)
        db.commit()
        
        return {
            "message": "Post deleted successfully",
            "post_id": id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete post: {str(e)}"
        )

# 게시글 수정 엔드포인트
@post_router.put("/{id}/edit")
def update_post(
    id: int, 
    post_data: PostUpdate,
    db: Session = Depends(get_db)
):
    try:
        # 게시글 존재 여부 확인
        post = db.exec(select(Post).where(Post.id == id)).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # 게시글 정보 업데이트
        post.item_name = post_data.item_name
        post.expected_price = post_data.expected_price
        post.description = post_data.description
        post.updated_date = datetime.now()
        
        if post_data.img_url:
            post.img_url = post_data.img_url
        
        db.add(post)
        db.commit()
        db.refresh(post)
        
        return {
            "message": "Post updated successfully",
            "post": {
                "id": post.id,
                "item_name": post.item_name,
                "expected_price": post.expected_price,
                "description": post.description,
                "img_url": post.img_url,
                "updated_date": post.updated_date
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update post: {str(e)}"
        )

@post_router.get("/{post_id}/offerlist", response_model=dict)
def get_post_offers(post_id: int, db: Session = Depends(get_db)):
    try:
        # 게시글 존재 여부 확인
        post = db.exec(select(Post).where(Post.id == post_id)).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # 해당 게시글의 모든 제안 조회
        offers = db.exec(select(Offer).where(Offer.post_id == post_id)).all()
        
        offers_list = []
        for offer in offers:
            # 각 제안에 대한 사용자 정보 조회
            offer_user = db.exec(select(User).where(User.id == offer.user_id)).first()
            
            offer_dict = {
                "id": offer.id,
                "user_id": offer.user_id,
                "post_id": offer.post_id,
                "offer_price": offer.offer_price,
                "created_date": offer.created_date,
                "is_accepted": offer.is_accepted,
                "email": offer_user.email if offer_user else None
            }
            offers_list.append(offer_dict)
            
        return {
            "offers": offers_list,
            "has_accepted_offer": any(offer["is_accepted"] for offer in offers_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch offers: {str(e)}"
        )